"""
fetch_commodities.py — World Bank Pink Sheet commodity prices relevant to Punjab
Runs monthly via GitHub Actions (monthly.yml).
Output: public/data/commodities.json + history/commodities_timeseries.json
No API key required — World Bank Open Data.
"""

import json, urllib.request, datetime, os, sys

# World Bank commodity price API (monthly, latest 12 months)
# Series: wheat (WHEAT), rice (RICE05), cotton (COTTON_A), natural gas India (NGAS_IND)
# sugar (SUGAR_WLD), palm oil (PALM500)
SERIES = {
    'wheat':    'WHEAT',
    'rice':     'RICE05',
    'cotton':   'COTTON_A',
    'sugar':    'SUGAR_WLD',
    'palm_oil': 'PALM500',
}

BASE_URL = 'https://api.worldbank.org/v2/en/indicator/PCOMM{}?format=json&per_page=12&mrv=12'

def fetch_series(code):
    url = f'https://api.worldbank.org/v2/en/indicator/PCOMM{code}?format=json&per_page=12&mrv=12'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'FALCON-PGIS/1.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode('utf-8'))
        # World Bank returns [meta, data_array]
        records = data[1] if len(data) > 1 else []
        if not records:
            return None
        # Most recent non-null value
        for rec in records:
            if rec.get('value') is not None:
                return {
                    'value': round(float(rec['value']), 2),
                    'date': rec['date'],
                    'unit': 'USD/mt',
                }
    except Exception as e:
        print(f'  Warning: could not fetch {code}: {e}')
    return None

print('Fetching World Bank commodity prices...')
prices = {}
for name, code in SERIES.items():
    result = fetch_series(code)
    if result:
        prices[name] = result
        print(f'  {name}: {result["value"]} {result["unit"]} ({result["date"]})')
    else:
        print(f'  {name}: unavailable')

# MSP reference values (INR/quintal, 2024-25 season — hardcoded annually)
MSP = {
    'wheat':  2275,
    'paddy':  2300,
    'cotton': 7121,
    'maize':  2090,
}

output = {
    'generated': datetime.datetime.utcnow().isoformat() + 'Z',
    'source': 'World Bank Pink Sheet',
    'note': 'International prices USD/mt; MSP in INR/quintal (GOI 2024-25)',
    'prices': prices,
    'msp_inr_quintal': MSP,
}

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out_path = os.path.join(base_dir, 'public', 'data', 'commodities.json')
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'w') as f:
    json.dump(output, f, separators=(',', ':'), indent=2)
print(f'Saved → {out_path}')

# Append to timeseries
today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
record = {'date': today}
for name, data in prices.items():
    record[name] = data['value']

ts_path = os.path.join(base_dir, 'public', 'data', 'history', 'commodities_timeseries.json')
try:
    with open(ts_path) as f:
        ts = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    ts = {'source': 'World Bank Pink Sheet', 'unit': 'USD/mt', 'records': []}

ts['records'] = [r for r in ts['records'] if r['date'] != today]
ts['records'].append(record)
ts['records'].sort(key=lambda r: r['date'])

os.makedirs(os.path.dirname(ts_path), exist_ok=True)
with open(ts_path, 'w') as f:
    json.dump(ts, f, separators=(',', ':'))
print(f'Timeseries: {len(ts["records"])} months → {ts_path}')
