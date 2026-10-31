"""
fetch_mandi.py — AGMARKNET mandi prices for Punjab
Uses data.gov.in open resource. No private API key needed.
Output: public/data/punjab_mandi.json
"""
import json, urllib.request, datetime, sys, os, urllib.parse

API_KEY = os.environ.get('DATAGOV_API_KEY', '579b464db66ec23bdd000001cdd3946e44ce4aebb836d8c9d4b3')
# AGMARKNET daily arrivals and prices — Punjab state
BASE_URL = (
    'https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070'
    f'?api-key={API_KEY}&format=json&limit=200'
    '&filters%5Bstate%5D=Punjab'
)

MANDI_COORDS = {
    'Amritsar':  [74.873,31.634], 'Ludhiana':  [75.857,30.901],
    'Jalandhar': [75.576,31.326], 'Patiala':   [76.386,30.339],
    'Bathinda':  [74.946,30.208], 'Sangrur':   [75.844,30.246],
    'Moga':      [75.174,30.818], 'Khanna':    [76.220,30.699],
    'Kapurthala':[75.381,31.380], 'Faridkot':  [74.759,30.674],
    'Muktsar':   [74.516,30.475], 'Mansa':     [75.391,29.988],
    'Barnala':   [75.546,30.378], 'Fazilka':   [74.023,30.405],
    'Gurdaspur': [75.406,32.041], 'Hoshiarpur':[75.912,31.533],
    'Firozpur':  [74.614,30.935], 'Nabha':     [76.150,30.376],
    'Rajpura':   [76.590,30.483], 'Morinda':   [76.499,30.791],
}

# MSP 2026-27 (Rs/quintal)
MSP = {'wheat':2275,'paddy':2320,'basmati':3800,'cotton':7020,
       'mustard':5650,'maize':2090,'sunflower':6760,'groundnut':6783}

def get_msp(commodity):
    c = commodity.lower()
    for k,v in MSP.items():
        if k in c: return v
    return None

print('Fetching AGMARKNET mandi prices for Punjab…')
try:
    req = urllib.request.Request(BASE_URL, headers={'User-Agent':'FALCON-PGIS/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr); sys.exit(1)

records = data.get('records', [])
print(f'Got {len(records)} records')

# Group by mandi, keep highest-value commodity per mandi
by_mandi = {}
for rec in records:
    mandi = rec.get('market','').strip()
    if not mandi: continue
    commodity = rec.get('commodity','').strip()
    try:
        modal = float(rec.get('modal_price') or rec.get('modal price') or 0)
    except: continue
    if modal <= 0: continue
    if mandi not in by_mandi or modal > by_mandi[mandi]['main_price']:
        by_mandi[mandi] = {
            'mandi': mandi,
            'main_crop': commodity,
            'main_price': modal,
            'date': rec.get('arrival_date', datetime.datetime.utcnow().strftime('%Y-%m-%d')),
        }

features = []
for mandi, info in by_mandi.items():
    coords = MANDI_COORDS.get(mandi)
    if not coords:
        for k,v in MANDI_COORDS.items():
            if k.lower() in mandi.lower(): coords=v; break
    if not coords: continue
    msp_val = get_msp(info['main_crop'])
    pct = round((info['main_price']/msp_val)*100,1) if msp_val else None
    features.append({'type':'Feature','geometry':{'type':'Point','coordinates':coords},
        'properties':{**info,'city':mandi,'msp':msp_val,'msp_pct':pct,
            'below_msp': pct is not None and pct < 100,'source':'AGMARKNET'}})

out = {'type':'FeatureCollection',
    'metadata':{'generated':datetime.datetime.utcnow().isoformat()+'Z',
        'source':'AGMARKNET via data.gov.in','count':len(features)},
    'features':features}

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'public','data','punjab_mandi.json')
with open(path,'w') as f: json.dump(out,f,separators=(',',':'))
print(f'Saved {len(features)} mandis -> {path}')

# --- Append to timeseries ---
import datetime as _dt
today = _dt.datetime.utcnow().strftime('%Y-%m-%d')

# Aggregate by commodity across all mandis
commodity_prices = {}
for feat in features:
    crop = feat['properties'].get('main_crop','')
    price = feat['properties'].get('main_price', 0)
    if not crop or not price: continue
    if crop not in commodity_prices:
        commodity_prices[crop] = []
    commodity_prices[crop].append(price)

record = {'date': today}
for crop, prices in commodity_prices.items():
    record[crop] = {
        'avg': round(sum(prices)/len(prices)),
        'min': min(prices),
        'max': max(prices),
    }

ts_path = os.path.join(os.path.dirname(path), 'history', 'mandi_timeseries.json')
try:
    with open(ts_path) as f:
        ts = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    ts = {'source': 'AGMARKNET', 'unit': 'Rs per quintal',
          'msp': {'wheat': 2275, 'paddy': 2320, 'cotton': 7020}, 'records': []}

ts['records'] = [r for r in ts['records'] if r['date'] != today]
ts['records'].append(record)
ts['records'].sort(key=lambda r: r['date'])

os.makedirs(os.path.dirname(ts_path), exist_ok=True)
with open(ts_path, 'w') as f:
    json.dump(ts, f, separators=(',', ':'))
print(f'Mandi timeseries: {len(ts["records"])} days recorded')
