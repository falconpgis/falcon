"""
fetch_aqi.py — CPCB Air Quality Index for Punjab stations
Runs daily via GitHub Actions.
Output: public/data/punjab_aqi.json
"""
import json, urllib.request, datetime, sys, os

API_KEY = os.environ.get('DATAGOV_API_KEY', '579b464db66ec23bdd000001cdd3946e44ce4aebb836d8c9d4b3')
AQI_URL = (
    'https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69'
    f'?api-key={API_KEY}&format=json&limit=100&filters%5Bstate%5D=Punjab'
)

STATION_COORDS = {
    'Amritsar':[74.873,31.634],'Ludhiana':[75.857,30.901],
    'Jalandhar':[75.576,31.326],'Patiala':[76.386,30.339],
    'Bathinda':[74.946,30.208],'Mandi Gobindgarh':[76.317,30.658],
    'Khanna':[76.220,30.699],'Rupnagar':[76.519,30.963],
    'Mohali':[76.716,30.705],'Pathankot':[75.652,32.274],
    'Firozpur':[74.614,30.935],'Gurdaspur':[75.406,32.041],
    'Hoshiarpur':[75.912,31.533],'Sangrur':[75.844,30.246],
    'Fatehgarh Sahib':[76.389,30.649],'Barnala':[75.546,30.378],
}

AQI_CATS = [(0,50,'Good','#00e400'),(51,100,'Satisfactory','#92d050'),
            (101,200,'Moderate','#ffff00'),(201,300,'Poor','#ff7e00'),
            (301,400,'Very Poor','#ff0000'),(401,999,'Severe','#99004c')]

def aqi_cat(v):
    for lo,hi,l,c in AQI_CATS:
        if lo<=v<=hi: return l,c
    return 'Severe','#99004c'

print('Fetching CPCB Punjab AQI…')
try:
    req = urllib.request.Request(AQI_URL, headers={'User-Agent':'FALCON-PGIS/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr); sys.exit(1)

records = data.get('records', [])
print(f'Got {len(records)} records')

features = []
for rec in records:
    city = rec.get('city', rec.get('station','')).strip()
    try: aqi_val = int(float(rec.get('aqi') or 0))
    except: continue
    if aqi_val <= 0: continue
    coords = STATION_COORDS.get(city)
    if not coords:
        for k,v in STATION_COORDS.items():
            if k.lower() in city.lower(): coords=v; break
    if not coords: continue
    cat, color = aqi_cat(aqi_val)
    features.append({'type':'Feature','geometry':{'type':'Point','coordinates':coords},
        'properties':{'station':rec.get('station',city),'city':city,'aqi':aqi_val,
            'category':cat,'color':color,'date':datetime.datetime.utcnow().strftime('%Y-%m-%d'),'source':'CPCB'}})

out = {'type':'FeatureCollection',
    'metadata':{'generated':datetime.datetime.utcnow().isoformat()+'Z','source':'CPCB','count':len(features)},
    'features':features}
path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'public','data','punjab_aqi.json')
with open(path,'w') as f: json.dump(out,f,separators=(',',':'))
print(f'Saved {len(features)} stations -> {path}')

# --- Append to timeseries ---
import datetime as _dt
today = _dt.datetime.utcnow().strftime('%Y-%m-%d')
station_aqi = {feat['properties']['city']: feat['properties']['aqi'] for feat in features}
record = {'date': today, 'stations': station_aqi}

ts_path = os.path.join(os.path.dirname(path), 'history', 'aqi_timeseries.json')
try:
    with open(ts_path) as f:
        ts = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    ts = {'source': 'CPCB SAMEER', 'unit': 'AQI', 'records': []}

ts['records'] = [r for r in ts['records'] if r['date'] != today]
ts['records'].append(record)
ts['records'].sort(key=lambda r: r['date'])

os.makedirs(os.path.dirname(ts_path), exist_ok=True)
with open(ts_path, 'w') as f:
    json.dump(ts, f, separators=(',', ':'))
print(f'AQI timeseries: {len(ts["records"])} days recorded')
