"""
fetch_trends.py — Google Trends for Punjab agriculture/distress keywords
Runs weekly via GitHub Actions. No API key needed (pytrends).
Output: public/data/punjab_trends.json
"""

import json, datetime, os, sys

try:
    from pytrends.request import TrendReq
except ImportError:
    print('Installing pytrends...')
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pytrends'])
    from pytrends.request import TrendReq

KEYWORDS = [
    'Punjab kisan',        # farmer
    'karz mafi Punjab',    # debt waiver Punjab
    'Punjab suicide',      # farmer distress signal
    'paddy stubble burning',
    'Amritsar AQI',
]

GEO = 'IN-PB'  # Punjab, India geo code

print(f'Fetching Google Trends for Punjab ({GEO})...')
pytrends = TrendReq(hl='en-US', tz=330)

results = {}
for kw in KEYWORDS:
    try:
        pytrends.build_payload([kw], timeframe='now 7-d', geo=GEO)
        df = pytrends.interest_over_time()
        if not df.empty and kw in df.columns:
            vals = df[kw].tolist()
            results[kw] = {
                'avg_7d': round(sum(vals) / len(vals), 1),
                'peak_7d': int(max(vals)),
                'last': int(vals[-1]) if vals else 0,
            }
            print(f'  {kw}: avg={results[kw]["avg_7d"]} peak={results[kw]["peak_7d"]}')
        else:
            print(f'  {kw}: no data')
    except Exception as e:
        print(f'  {kw}: error — {e}')

output = {
    'generated': datetime.datetime.utcnow().isoformat() + 'Z',
    'source': 'Google Trends (pytrends)',
    'geo': GEO,
    'note': 'Relative interest 0-100 within Punjab, India; 7-day window',
    'keywords': results,
}

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out_path = os.path.join(base_dir, 'public', 'data', 'punjab_trends.json')
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'w') as f:
    json.dump(output, f, separators=(',', ':'), indent=2)
print(f'Saved → {out_path}')
