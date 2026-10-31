"""
fetch_currencies.py — Exchange rates relevant to Punjab/Sikh diaspora
Uses exchangerate-api.com free tier (no key needed for basic endpoint).
Output: public/data/currencies.json
"""
import json, urllib.request, datetime, sys, os

# Free endpoint, no key needed
URL = 'https://open.er-api.com/v6/latest/INR'

# Currencies relevant to Sikh diaspora and Punjab economy
TRACK = {
    'USD': 'US Dollar',
    'CAD': 'Canadian Dollar',
    'GBP': 'British Pound',
    'AED': 'UAE Dirham',
    'EUR': 'Euro',
    'AUD': 'Australian Dollar',
    'SGD': 'Singapore Dollar',
    'PKR': 'Pakistani Rupee',
    'MYR': 'Malaysian Ringgit',
    'NZD': 'New Zealand Dollar',
}

print('Fetching exchange rates (INR base)…')
try:
    req = urllib.request.Request(URL, headers={'User-Agent':'FALCON-PGIS/1.0'})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr); sys.exit(1)

rates_raw = data.get('rates', {})
# Rates are how much 1 INR buys in each currency
# Flip to: how many INR does 1 unit of foreign currency cost
rates = {}
for code, label in TRACK.items():
    raw = rates_raw.get(code)
    if raw and raw > 0:
        rates[code] = {'label': label, 'per_inr': round(raw, 6), 'inr_per_unit': round(1/raw, 4)}

out = {
    'generated': datetime.datetime.utcnow().isoformat() + 'Z',
    'base': 'INR',
    'source': 'open.er-api.com',
    'rates': rates,
}

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'public','data','currencies.json')
with open(path,'w') as f: json.dump(out,f,separators=(',',':'))
print(f'Saved {len(rates)} currency rates -> {path}')
for code, info in rates.items():
    print(f'  1 {code} = ₹{info["inr_per_unit"]}')
