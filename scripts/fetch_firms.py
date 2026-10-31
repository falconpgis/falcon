"""
fetch_firms.py — NASA FIRMS VIIRS NRT fire hotspots for Punjab
Runs daily via GitHub Actions. Requires FIRMS_MAP_KEY env var.
Output: public/data/punjab_fires.geojson
"""

import os, json, csv, io, urllib.request, datetime, sys

MAP_KEY = os.environ.get('FIRMS_MAP_KEY', '')
if not MAP_KEY:
    print('ERROR: FIRMS_MAP_KEY not set', file=sys.stderr)
    sys.exit(1)

# Punjab bounding box: west,south,east,north (FIRMS area API format)
W, S, E, N = 73.8, 29.5, 76.9, 32.5
DAYS = 5   # last 5 days (FIRMS NRT max)

# FIRMS area API: /api/area/csv/{key}/{source}/{west,south,east,north}/{days}
url = (
    f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/'
    f'{MAP_KEY}/VIIRS_SNPP_NRT/{W},{S},{E},{N}/{DAYS}'
)

print(f'Fetching: {url}')
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'FALCON-PGIS/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode('utf-8')
        print(f'Response ({r.status}): first 200 chars: {raw[:200]}')
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f'ERROR HTTP {e.code}: {body[:500]}', file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}', file=sys.stderr)
    sys.exit(1)

# Parse CSV response
reader = csv.DictReader(io.StringIO(raw))
fires  = list(reader)
print(f'Found {len(fires)} fire detections')
if fires:
    print(f'CSV columns: {list(fires[0].keys())}')

features = []
for f in fires:
    try:
        lon  = float(f.get('longitude') or f.get('Longitude', 0))
        lat  = float(f.get('latitude')  or f.get('Latitude',  0))
        frp  = float(f.get('frp', 0) or 0)
        conf = (f.get('confidence') or f.get('Confidence') or 'n').strip().lower()
        conf = conf[0] if conf else 'n'
        acq_date = f.get('acq_date', '')
        acq_time = f.get('acq_time', '')
        bright   = float(f.get('bright_ti4') or f.get('brightness', 0) or 0)

        features.append({
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [lon, lat]},
            'properties': {
                'date':       acq_date,
                'time':       acq_time,
                'frp':        frp,
                'brightness': bright,
                'confidence': conf,
                'source':     'NASA FIRMS VIIRS SNPP NRT',
            }
        })
    except (KeyError, ValueError) as e:
        print(f'Skipping row: {e}')
        continue

geojson = {
    'type': 'FeatureCollection',
    'metadata': {
        'generated': datetime.datetime.utcnow().isoformat() + 'Z',
        'source':    'NASA FIRMS VIIRS SNPP NRT',
        'bounds':    f'{W},{S},{E},{N}',
        'days':      DAYS,
        'count':     len(features),
    },
    'features': features,
}

out_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'public', 'data', 'punjab_fires.geojson'
)
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'w', encoding='utf-8') as fh:
    json.dump(geojson, fh, separators=(',', ':'))

print(f'Saved {len(features)} features → {out_path}')

# --- Append to timeseries ---
today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
frp_vals = [f['properties']['frp'] for f in features if f['properties']['frp'] > 0]
record = {
    'date':     today,
    'count':    len(features),
    'peak_frp': round(max(frp_vals), 1) if frp_vals else 0,
    'avg_frp':  round(sum(frp_vals) / len(frp_vals), 1) if frp_vals else 0,
}

ts_path = os.path.join(os.path.dirname(out_path), 'history', 'fires_timeseries.json')
try:
    with open(ts_path) as f:
        ts = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    ts = {'source': 'NASA FIRMS VIIRS NRT', 'unit': 'count/day', 'records': []}

# Replace today's record if exists, else append
ts['records'] = [r for r in ts['records'] if r['date'] != today]
ts['records'].append(record)
ts['records'].sort(key=lambda r: r['date'])

os.makedirs(os.path.dirname(ts_path), exist_ok=True)
with open(ts_path, 'w') as f:
    json.dump(ts, f, separators=(',', ':'))
print(f'Timeseries: {len(ts["records"])} days recorded → {ts_path}')
