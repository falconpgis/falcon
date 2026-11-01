"""
FALCON — Engine III: UN Comtrade trade flow fetcher
Subscription key required: set env var COMTRADE_KEY
API docs: https://comtradeapi.un.org/

Pulls for FALCON:
  - Wheat (1001), Rice (1006), Potash (3104), Urea (3102) — global + Punjab-relevant partners
  - India bilateral trade: Pakistan, Canada, Russia, China, USA, UAE
  - De-dollarisation signal: India–Russia trade in non-USD terms (proxy: trade value growth)
"""

import os, json, time, datetime, requests
from pathlib import Path

API_KEY  = os.environ.get("COMTRADE_KEY", "")
BASE     = "https://comtradeapi.un.org/data/v1/get"
DATA_DIR = Path(__file__).parent.parent / "public" / "data"
HIST_DIR = DATA_DIR / "history"
HIST_DIR.mkdir(parents=True, exist_ok=True)

# ISO numeric country codes
COUNTRIES = {
    "India":    356,
    "Pakistan": 586,
    "Canada":   124,
    "Russia":   643,
    "China":    156,
    "USA":      842,
    "UAE":      784,
    "Ukraine":  804,
    "World":    0,
}

# HS commodity codes relevant to Punjab / geopolitics
COMMODITIES = {
    "wheat":         "1001",   # wheat and meslin
    "rice":          "1006",   # rice (Punjab's main crop)
    "potash":        "3104",   # potassium fertilisers
    "urea":          "3102",   # nitrogen fertilisers
    "cotton":        "5201",   # cotton (Punjab Malwa belt)
    "crude_oil":     "2709",   # crude petroleum
    "natural_gas":   "2711",   # natural gas (Russia signal)
    "semiconductors":"8542",   # integrated circuits (tech sovereignty)
}

HEADERS = {
    "Ocp-Apim-Subscription-Key": API_KEY,
    "Accept": "application/json",
}

def comtrade_get(reporter, partner, cmd_code, flow="M", freq="A", period=None):
    """Single Comtrade API call. Returns list of data rows or []."""
    if not API_KEY:
        print("  [skip] COMTRADE_KEY not set")
        return []
    if period is None:
        period = str(datetime.datetime.utcnow().year - 1)  # last full year
    url = f"{BASE}/C/{freq}/HS"
    params = {
        "reporterCode": reporter,
        "partnerCode":  partner,
        "cmdCode":      cmd_code,
        "flowCode":     flow,
        "period":       period,
        "maxRecords":   500,
        "format":       "JSON",
        "breakdownMode":"classic",
    }
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        return data.get("data", [])
    except Exception as e:
        print(f"  [warn] comtrade {reporter}->{partner} {cmd_code}: {e}")
        return []

def usd_value(rows):
    """Sum CIF/FOB trade value in USD from rows."""
    return sum(r.get("primaryValue", 0) or 0 for r in rows)

def tonnes(rows):
    """Sum net weight (kg→tonnes) from rows."""
    return round(sum(r.get("netWgt", 0) or 0 for r in rows) / 1000)

def fetch_food_security():
    """
    Global wheat and rice trade — who is exposed if supply disrupts.
    Key: India is world's largest rice exporter. Ukraine is top wheat exporter.
    Punjab groundwater depletion → India rice export capacity risk.
    """
    print("Fetching food security trade flows...")
    year = str(datetime.datetime.utcnow().year - 1)
    out = {}

    # India wheat imports (MSP regime means India rarely imports — signal if it does)
    rows = comtrade_get(COUNTRIES["India"], COUNTRIES["World"], COMMODITIES["wheat"], flow="M", period=year)
    out["india_wheat_imports_usd"] = usd_value(rows)
    out["india_wheat_imports_t"]   = tonnes(rows)
    time.sleep(1)

    # India rice exports (world's largest — Punjab groundwater risk flows here)
    rows = comtrade_get(COUNTRIES["India"], COUNTRIES["World"], COMMODITIES["rice"], flow="X", period=year)
    out["india_rice_exports_usd"] = usd_value(rows)
    out["india_rice_exports_t"]   = tonnes(rows)
    time.sleep(1)

    # Pakistan wheat imports (food security pressure → conflict risk)
    rows = comtrade_get(COUNTRIES["Pakistan"], COUNTRIES["World"], COMMODITIES["wheat"], flow="M", period=year)
    out["pakistan_wheat_imports_usd"] = usd_value(rows)
    time.sleep(1)

    # India potash imports (fertiliser = Punjab farm cost signal)
    rows = comtrade_get(COUNTRIES["India"], COUNTRIES["World"], COMMODITIES["potash"], flow="M", period=year)
    out["india_potash_imports_usd"] = usd_value(rows)
    time.sleep(1)

    # India urea imports
    rows = comtrade_get(COUNTRIES["India"], COUNTRIES["World"], COMMODITIES["urea"], flow="M", period=year)
    out["india_urea_imports_usd"] = usd_value(rows)
    time.sleep(1)

    out["year"] = year
    return out

def fetch_india_bilateral():
    """
    India's bilateral trade with key partners — alignment signal.
    Russia: growing despite sanctions = de-dollarisation, non-West alignment
    Canada: declining = diaspora corridor risk elevated
    China: high but fraught = SCO alignment mixed
    USA: growing = QUAD/West alignment
    """
    print("Fetching India bilateral trade flows...")
    year = str(datetime.datetime.utcnow().year - 1)
    out = {}

    partners = {
        "russia": COUNTRIES["Russia"],
        "canada": COUNTRIES["Canada"],
        "china":  COUNTRIES["China"],
        "usa":    COUNTRIES["USA"],
        "uae":    COUNTRIES["UAE"],
        "pakistan": COUNTRIES["Pakistan"],
    }

    for name, code in partners.items():
        # Total imports from partner (all commodities = "TOTAL" or use AG2 level)
        rows_m = comtrade_get(COUNTRIES["India"], code, "TOTAL", flow="M", period=year)
        rows_x = comtrade_get(COUNTRIES["India"], code, "TOTAL", flow="X", period=year)
        out[f"india_{name}_imports_usd"] = usd_value(rows_m)
        out[f"india_{name}_exports_usd"] = usd_value(rows_x)
        out[f"india_{name}_total_usd"]   = usd_value(rows_m) + usd_value(rows_x)
        time.sleep(1.5)

    # Crude oil: India from Russia (post-sanctions signal)
    rows = comtrade_get(COUNTRIES["India"], COUNTRIES["Russia"], COMMODITIES["crude_oil"], flow="M", period=year)
    out["india_russia_crude_imports_usd"] = usd_value(rows)
    out["india_russia_crude_imports_t"]   = tonnes(rows)
    time.sleep(1)

    out["year"] = year
    return out

def fetch_semiconductor_exposure():
    """
    Semiconductor / IC trade — tech sovereignty signal.
    India dependency on China/USA for chips affects tech sector which NRI diaspora relies on.
    """
    print("Fetching semiconductor trade flows...")
    year = str(datetime.datetime.utcnow().year - 1)
    out = {}

    rows = comtrade_get(COUNTRIES["India"], COUNTRIES["China"], COMMODITIES["semiconductors"], flow="M", period=year)
    out["india_china_chip_imports_usd"] = usd_value(rows)
    time.sleep(1)

    rows = comtrade_get(COUNTRIES["India"], COUNTRIES["USA"], COMMODITIES["semiconductors"], flow="M", period=year)
    out["india_usa_chip_imports_usd"] = usd_value(rows)
    time.sleep(1)

    out["year"] = year
    return out

def derive_signals(food, bilateral, semi):
    """
    Derive FALCON prediction signals from trade data.
    """
    signals = {}

    # Russia alignment signal: Russia crude as % of India total imports proxy
    russia_crude = bilateral.get("india_russia_crude_imports_usd", 0)
    russia_total = bilateral.get("india_russia_total_usd", 0)
    if russia_total > 0:
        signals["russia_trade_intensity"] = round(russia_crude / russia_total * 100, 1)
    else:
        signals["russia_trade_intensity"] = None

    # Canada-India tension proxy: if Canada trade declined, flag
    canada_total = bilateral.get("india_canada_total_usd", 0)
    signals["india_canada_trade_usd"] = canada_total

    # Food security: Pakistan import pressure
    pak_wheat = food.get("pakistan_wheat_imports_usd", 0)
    signals["pakistan_wheat_import_pressure"] = "HIGH" if pak_wheat > 1_500_000_000 else "MODERATE" if pak_wheat > 500_000_000 else "LOW"

    # Punjab fertiliser cost: potash + urea imports
    potash = food.get("india_potash_imports_usd", 0)
    urea   = food.get("india_urea_imports_usd", 0)
    signals["india_fertiliser_imports_usd"] = potash + urea

    # Tech dependency: chip imports from China vs USA
    china_chips = semi.get("india_china_chip_imports_usd", 0)
    usa_chips   = semi.get("india_usa_chip_imports_usd", 0)
    total_chips = china_chips + usa_chips
    if total_chips > 0:
        signals["chip_china_pct"] = round(china_chips / total_chips * 100, 1)
    else:
        signals["chip_china_pct"] = None

    return signals

def main():
    print("FALCON · fetch_comtrade.py")
    print(f"API key present: {'yes' if API_KEY else 'NO — set COMTRADE_KEY'}")

    food      = fetch_food_security()
    bilateral = fetch_india_bilateral()
    semi      = fetch_semiconductor_exposure()
    signals   = derive_signals(food, bilateral, semi)

    out = {
        "fetched_utc":    datetime.datetime.utcnow().isoformat() + "Z",
        "data_year":      food.get("year"),
        "food_security":  food,
        "india_bilateral":bilateral,
        "semiconductors": semi,
        "falcon_signals": signals,
    }

    # Write current snapshot
    snap_path = DATA_DIR / "comtrade.json"
    snap_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Written: {snap_path}")

    # Append to history timeseries
    hist_path = HIST_DIR / "comtrade_timeseries.json"
    history = []
    if hist_path.exists():
        try:
            history = json.loads(hist_path.read_text(encoding="utf-8"))
        except Exception:
            history = []
    history.append({
        "date":     datetime.datetime.utcnow().strftime("%Y-%m-%d"),
        "year":     food.get("year"),
        "signals":  signals,
    })
    history = history[-60:]  # keep 5 years of annual snapshots
    hist_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    print(f"History: {hist_path} ({len(history)} entries)")

    # Print key signals
    print("\n── FALCON signals from Comtrade ──")
    for k, v in signals.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
