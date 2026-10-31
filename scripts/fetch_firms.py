"""
fetch_firms.py — NASA FIRMS VIIRS NRT fire hotspots for Punjab
Runs daily via GitHub Actions. Requires FIRMS_MAP_KEY env var.
Output: public/data/punjab_fires.geojson
"""

import os, json, urllib.request, datetime, sys

MAP_KEY = os.environ.get('FIRMS_MAP_KEY', '')
if not MAP_KEY:
    print('ERROR: FIRMS_MAP_KEY not set', file=sys.stderr)
    sys.exit(1)

# Punjab bounding box: west,south,east,north
BOUNDS = '73.8,29.5,76.9,32.5'
DAYS   = 2   # last 2 days to catch any overnight fires

url = (
    f'https://firms.modaps.eosdis.nasa.gov/api/area/json/'
    f'{MAP_KEY}/VIIRS_SNPP_NRT/{BOUNDS}/{DAYS}'
)

print(f'Fetching FIRMS data for Punjab (last {DAYS} days)…')
try:
    with urllib.request.urlopen(url, timeout=30) as r:
        fires = json.loads(r.read().decode())
except Exception as e:
    print(f'ERROR fetching FIRMS: {e}', file=sys.stderr)
    sys.exit(1)

print(f'Found {len(fires)} fire detections')

features = []
for f in fires:
    try:
        lon  = float(f['longitude'])
        lat  = float(f['latitude'])
        frp  = float(f.get('frp', 0))        # Fire Radiative Power (MW)
        conf = f.get('confidence', 'n')       # n=nominal, h=high, l=low
        acq_date = f.get('acq_date', '')
        acq_time = f.get('acq_time', '')
        bright   = float(f.get('bright_ti4', 0))

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
    except (KeyError, ValueError):
        continue

geojson = {
    'type': 'FeatureCollection',
    'metadata': {
        'generated': datetime.datetime.utcnow().isoformat() + 'Z',
        'source':    'NASA FIRMS VIIRS SNPP NRT',
        'bounds':    BOUNDS,
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
