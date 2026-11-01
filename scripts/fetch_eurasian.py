"""
fetch_eurasian.py — Eurasian signals that directly affect Punjab
ALL FREE, NO API KEY REQUIRED:
  - World Bank Commodity Price API (free, no key)
  - Stooq.com Baltic Dry Index (free CSV)
  - frankfurter.app currency history (free, no key)
  - IMF WEO data (free)
  - UN Comtrade bulk data (free)
Output:
  public/data/eurasian_signals.json
  public/data/history/commodities_timeseries.json
  public/data/history/currencies_timeseries.json
  public/data/history/bdi_timeseries.json
"""

import json, urllib.request, datetime, os, sys, time, csv, io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'public', 'data')
HIST = os.path.join(DATA, 'history')
os.makedirs(HIST, exist_ok=True)

TODAY = datetime.datetime.utcnow().strftime('%Y-%m-%d')
NOW   = datetime.datetime.utcnow().isoformat() + 'Z'
YEAR  = datetime.datetime.utcnow().year

def fetch_url(url, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent':'FALCON-PGIS/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print(f'  WARN {url[:60]}: {e}')
        return None

# ── 1. World Bank Commodity Prices (free JSON API, no key) ───────────────────
# CMO Pink Sheet API
WB_COMMODITIES = {
    'wheat_us':  ('WHEAT_US_HRW', 'Wheat US HRW', 'USD/mt'),
    'rice':      ('RICE_05',       'Rice Thai 5%', 'USD/mt'),
    'cotton':    ('COTTON_A_INDX', 'Cotton A-Index','USD/kg'),
    'potash':    ('POTASH',        'Potash MOP',   'USD/mt'),
    'urea':      ('UREA_EE_BULK',  'Urea bulk',    'USD/mt'),
    'dap':       ('DAP',           'DAP fertilizer','USD/mt'),
    'crude_brent':('CRUDE_BRENT',  'Brent crude',  'USD/bbl'),
    'palm_oil':  ('PALM_OIL',      'Palm oil',     'USD/mt'),
    'natural_gas_eu':('NGAS_EUR',  'Nat gas Europe','USD/mmbtu'),
}

def fetch_wb_commodity(indicator, lookback_months=24):
    """World Bank API — returns monthly price data."""
    # World Bank data API format
    url = (
        f'https://api.worldbank.org/v2/en/indicator/{indicator}'
        f'?format=json&per_page=30&mrv={lookback_months}&frequency=M'
    )
    raw = fetch_url(url)
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if not isinstance(data, list) or len(data) < 2:
            return []
        records = data[1] or []
        result = []
        for r in records:
            if r.get('value') is not None:
                result.append({'date': r['date'], 'value': round(float(r['value']), 2)})
        result.sort(key=lambda x: x['date'])
        return result
    except:
        return []

# Alternative: World Bank Pink Sheet direct CSV (monthly)
PINK_SHEET_URL = 'https://thedocs.worldbank.org/en/doc/5d903e848db1d1b83e0ec8f744e55570-0350012021/related/CMO-Pink-Sheet-December-2021.xlsx'

# Use the commodity monitor JSON endpoint instead
def fetch_wb_pink_sheet():
    """Fetch World Bank commodity monitor data."""
    # POTASH, UREA, DAP via the API
    results = {}
    for key, (indicator, label, unit) in WB_COMMODITIES.items():
        print(f'  WB {key} ({indicator})...')
        # The World Bank commodity price indicator codes
        # Use the CMO API: api.worldbank.org/v2/commodity
        url = f'https://api.worldbank.org/v2/en/indicator/PCOMM.{indicator}?format=json&mrv=3&frequency=M'
        raw = fetch_url(url)
        val = None
        if raw:
            try:
                d = json.loads(raw)
                if isinstance(d, list) and len(d) > 1 and d[1]:
                    for rec in d[1]:
                        if rec.get('value') is not None:
                            val = round(float(rec['value']), 2)
                            break
            except:
                pass
        results[key] = {'label': label, 'unit': unit, 'value': val, 'date': TODAY}
        time.sleep(0.3)
    return results

# ── 2. Baltic Dry Index from stooq.com (free CSV) ────────────────────────────
def fetch_bdi():
    """Fetch Baltic Dry Index from stooq.com — free, no key."""
    # stooq provides free historical data
    url = 'https://stooq.com/q/d/l/?s=bdi&i=d'
    raw = fetch_url(url)
    if not raw:
        return None, []
    try:
        text = raw.decode('utf-8', errors='replace')
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            return None, []
        # rows format: Date, Open, High, Low, Close, Volume
        history = []
        for row in rows[-90:]:  # last 90 days
            try:
                history.append({
                    'date':  row.get('Date',''),
                    'close': float(row.get('Close', 0) or 0),
                })
            except:
                continue
        latest = history[-1]['close'] if history else None
        return latest, history
    except Exception as e:
        print(f'  BDI parse error: {e}')
        return None, []

# ── 3. Currency history from frankfurter.app (free, no key) ──────────────────
# Tracks diaspora currency rates daily
DISP_CURRENCIES = ['CAD', 'GBP', 'EUR', 'AED', 'AUD', 'USD', 'PKR']

def fetch_currency_history_days(days=30):
    """Fetch last N days of currency rates from INR base."""
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days)
    url = (
        f'https://api.frankfurter.app/{start}..{end}'
        f'?base=INR&symbols={",".join(DISP_CURRENCIES)}'
    )
    raw = fetch_url(url)
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data.get('rates', {})  # {date: {CAD: x, GBP: y...}}
    except:
        return {}

# ── 4. Punjab SDL yield spread proxy via RBI (public data) ───────────────────
def fetch_rbi_gsec_yield():
    """Fetch India 10Y G-Sec yield from RBI DBIE (free, public)."""
    # RBI publishes yield data; approximation from public bond prices
    # Fallback: use alternative free source
    url = 'https://fbil.org.in/json_data/ReferenceRate.json'
    raw = fetch_url(url)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        # FBIL publishes reference rates
        return data
    except:
        return None

# ── Run ───────────────────────────────────────────────────────────────────────
print('=== FALCON Eurasian Signals ===')

signals = {
    'generated': NOW,
    'date': TODAY,
    'note': 'All free sources, no API keys required',
}

# World Bank commodities
print('\n[1] World Bank commodity prices...')
# Use direct Pink Sheet commodities endpoint
def fetch_pink_sheet_simple():
    """Simpler World Bank commodity fetch using the indicator API."""
    # Key commodities for Punjab
    INDICATORS = {
        'wheat':     ('PWHEAMT',    'Wheat (US HRW)',  'USD/mt'),
        'rice':      ('PRICENPQ',   'Rice (Thai 5%)',  'USD/mt'),
        'potash':    ('PPOTAMTE',   'Potash',          'USD/mt'),
        'urea':      ('PUREA',      'Urea (bulk)',      'USD/mt'),
        'dap':       ('PDAP',       'DAP fertilizer',  'USD/mt'),
        'crude':     ('POILBRE',    'Brent crude',     'USD/bbl'),
        'palm_oil':  ('PPALMTE',    'Palm oil',        'USD/mt'),
        'nat_gas_eu':('PNGASEUQ',   'Natural gas EU',  'USD/mmbtu'),
        'cotton':    ('PCOTTIND',   'Cotton A-Index',  'USD/kg'),
    }
    out = {}
    for key, (ind, label, unit) in INDICATORS.items():
        url = f'https://api.worldbank.org/v2/indicator/{ind}?format=json&mrv=3&per_page=3'
        raw = fetch_url(url)
        val = date_val = None
        if raw:
            try:
                d = json.loads(raw)
                for rec in (d[1] if isinstance(d,list) and len(d)>1 else []):
                    if rec.get('value') is not None:
                        val = round(float(rec['value']), 2)
                        date_val = rec.get('date','')
                        break
            except:
                pass
        out[key] = {'label': label, 'unit': unit, 'value': val, 'wb_date': date_val}
        print(f'  {key}: {val} {unit} ({date_val})')
        time.sleep(0.2)
    return out

commodities = fetch_pink_sheet_simple()
signals['commodities'] = commodities

# Baltic Dry Index
print('\n[2] Baltic Dry Index...')
bdi_latest, bdi_history = fetch_bdi()
if bdi_latest:
    print(f'  BDI: {bdi_latest}')
signals['baltic_dry_index'] = {
    'value': bdi_latest,
    'date': TODAY,
    'label': 'Baltic Dry Index',
    'note': 'Bulk shipping cost; higher = costlier fertiliser imports for Punjab',
}

# Currency history
print('\n[3] Currency history (30 days)...')
cur_history_raw = fetch_currency_history_days(30)
# Restructure: {currency: [values_by_date]}
cur_by_code = {code: [] for code in DISP_CURRENCIES}
for date_str, rates in sorted(cur_history_raw.items()):
    for code in DISP_CURRENCIES:
        if code in rates and rates[code] > 0:
            cur_by_code[code].append({
                'date': date_str,
                'per_inr': round(rates[code], 6),
                'inr_per_unit': round(1.0 / rates[code], 4),
            })

signals['currency_30d'] = {
    code: {
        'latest': vals[-1]['inr_per_unit'] if vals else None,
        'change_30d_pct': (
            round(((vals[-1]['inr_per_unit'] - vals[0]['inr_per_unit'])
                   / vals[0]['inr_per_unit'] * 100), 2)
            if vals and len(vals) > 1 else None
        ),
    }
    for code, vals in cur_by_code.items()
}

# ── Save main signals file ───────────────────────────────────────────────────
path_s = os.path.join(DATA, 'eurasian_signals.json')
with open(path_s, 'w') as f:
    json.dump(signals, f, separators=(',', ':'))
print(f'\nSaved eurasian_signals.json -> {path_s}')

# ── Append commodities timeseries ────────────────────────────────────────────
ts_com_path = os.path.join(HIST, 'commodities_timeseries.json')
try:
    with open(ts_com_path) as f:
        ts_com = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    ts_com = {'source': 'World Bank Pink Sheet', 'records': []}

com_rec = {'date': TODAY}
for key, info in commodities.items():
    if info.get('value') is not None:
        com_rec[key] = info['value']
com_rec['bdi'] = bdi_latest

ts_com['records'] = [r for r in ts_com['records'] if r['date'] != TODAY]
ts_com['records'].append(com_rec)
ts_com['records'].sort(key=lambda r: r['date'])
ts_com['records'] = ts_com['records'][-520:]  # ~10 years of weekly records

with open(ts_com_path, 'w') as f:
    json.dump(ts_com, f, separators=(',', ':'))
print(f'Commodities timeseries: {len(ts_com["records"])} records')

# ── Append BDI timeseries ────────────────────────────────────────────────────
if bdi_history:
    ts_bdi_path = os.path.join(HIST, 'bdi_timeseries.json')
    try:
        with open(ts_bdi_path) as f:
            ts_bdi = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        ts_bdi = {'source': 'Baltic Exchange via stooq.com', 'records': []}

    existing_dates = {r['date'] for r in ts_bdi.get('records', [])}
    for rec in bdi_history:
        if rec['date'] not in existing_dates:
            ts_bdi.setdefault('records', []).append(rec)

    ts_bdi['records'].sort(key=lambda r: r['date'])
    ts_bdi['records'] = ts_bdi['records'][-1825:]  # 5 years

    with open(ts_bdi_path, 'w') as f:
        json.dump(ts_bdi, f, separators=(',', ':'))
    print(f'BDI timeseries: {len(ts_bdi["records"])} records')

# ── Append currency timeseries ────────────────────────────────────────────────
ts_cur_path = os.path.join(HIST, 'currencies_timeseries.json')
try:
    with open(ts_cur_path) as f:
        ts_cur = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    ts_cur = {'source': 'frankfurter.app / ECB', 'base': 'INR', 'records': []}

existing_dates = {r['date'] for r in ts_cur.get('records', [])}
for date_str, rates in sorted(cur_history_raw.items()):
    if date_str not in existing_dates:
        rec = {'date': date_str}
        for code in DISP_CURRENCIES:
            if code in rates and rates[code] > 0:
                rec[code] = round(1.0 / rates[code], 4)  # inr_per_unit
        ts_cur.setdefault('records', []).append(rec)

ts_cur['records'].sort(key=lambda r: r['date'])
ts_cur['records'] = ts_cur['records'][-3650:]  # 10 years

with open(ts_cur_path, 'w') as f:
    json.dump(ts_cur, f, separators=(',', ':'))
print(f'Currency timeseries: {len(ts_cur["records"])} records')
