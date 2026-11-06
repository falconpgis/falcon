"""
FALCON — Engine I + IV: SIPRI arms transfers + military expenditure
Source: SIPRI Open Data (Stockholm International Peace Research Institute)
        SIPRI Arms Transfers Database — public annual data
        SIPRI Military Expenditure Database — public annual data

No API key required. Uses SIPRI's public CSV exports.

Outputs:
  public/data/sipri_arms.json
  public/data/history/sipri_timeseries.json
"""
import json, datetime, requests, csv, io
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "public" / "data"
HIST_DIR = DATA_DIR / "history"
HIST_DIR.mkdir(parents=True, exist_ok=True)

# SIPRI public data exports (no key needed)
# Military expenditure data via World Bank (SIPRI provides data to WB)
# WB indicator MS.MIL.XPND.CD = military expenditure in current USD (SIPRI source)
WB_MIL_EXP_URL = "https://api.worldbank.org/v2/country/{country}/indicator/MS.MIL.XPND.CD?format=json&mrv=5&per_page=5"
WB_MIL_GNP_URL = "https://api.worldbank.org/v2/country/{country}/indicator/MS.MIL.XPND.GD.ZS?format=json&mrv=5&per_page=5"

# SIPRI Fact Sheets public page (for most recent data)
SIPRI_FACTS_URL = "https://sipri.org/sites/default/files/MILEX%20data%201949-2023.xlsx"

# Countries with arms/military relevance to Punjab
MILITARY_COUNTRIES = {
    "IN": "India",
    "PK": "Pakistan",
    "CN": "China",
    "RU": "Russia",
    "US": "United States",
    "SA": "Saudi Arabia",
    "AE": "UAE",
    "IR": "Iran",
    "AF": "Afghanistan",
    "TR": "Turkey",
    "IL": "Israel",
    "KZ": "Kazakhstan",
    "GB": "United Kingdom",
    "FR": "France",
}

# Supplementary arms trade context from public records
KNOWN_ARMS_TRANSFERS = {
    "India": {
        "major_suppliers": ["Russia", "France", "Israel", "United States"],
        "systems": {
            "S-400 (Russia)": {"delivered": 2021, "qty": "5 regiments"},
            "Rafale (France)": {"delivered": 2020, "qty": "36 aircraft"},
            "INS Vikrant (domestic)": {"delivered": 2022, "qty": "1 carrier"},
            "Apache helicopters (US)": {"delivered": 2019, "qty": "22"},
        },
        "note": "World's largest arms importer 2019-2023 (SIPRI)"
    },
    "Pakistan": {
        "major_suppliers": ["China", "United States (pre-2010)", "Turkey"],
        "systems": {
            "JF-17 Thunder (China/Pakistan)": {"delivered": "ongoing", "qty": "140+"},
            "HAROP drone (Israel)": {"delivered": "reported 2015", "qty": "unknown"},
            "HQ-9/P (China)": {"delivered": "2021", "qty": "reported"},
        },
        "note": "China supplies ~70% of Pakistan arms imports (SIPRI 2019-2023)"
    },
    "China": {
        "major_suppliers": ["domestic"],
        "note": "Self-sufficient; world's 4th largest arms exporter"
    },
    "Russia": {
        "major_suppliers": ["domestic"],
        "note": "World's 2nd largest arms exporter; exports strained by Ukraine war"
    },
}

def fetch_wb_mil(country_code, indicator_url):
    url = indicator_url.format(country=country_code)
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and len(data) > 1:
            for e in (data[1] or []):
                if e.get("value") is not None:
                    return {"year": e["date"], "value": round(float(e["value"]), 2)}
        return None
    except Exception as e:
        print(f"[warn] WB mil {country_code}: {e}")
        return None

def main():
    print("FALCON · fetch_sipri.py")
    now = datetime.datetime.utcnow()

    result = {
        "generated_at": now.isoformat() + "Z",
        "source":        "SIPRI (via World Bank API) + SIPRI public records",
        "note":          "Military expenditure in current USD. Arms transfers from SIPRI public annual reports.",
        "military_expenditure": {},
        "arms_transfers_context": KNOWN_ARMS_TRANSFERS,
    }

    # Fetch military expenditure for all countries
    for code, name in MILITARY_COUNTRIES.items():
        spend = fetch_wb_mil(code, WB_MIL_EXP_URL)
        pct   = fetch_wb_mil(code, WB_MIL_GNP_URL)
        if spend or pct:
            result["military_expenditure"][name] = {
                "code":          code,
                "expenditure_usd": spend,
                "pct_gdp":       pct,
            }
            spend_str = f"${spend['value']/1e9:.1f}B ({spend['year']})" if spend else "—"
            pct_str   = f"{pct['value']:.1f}% GDP" if pct else "—"
            print(f"  {name:20} {spend_str:20} {pct_str}")
        else:
            print(f"  {name:20} — no data")

    out_path = DATA_DIR / "sipri_arms.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Written: {out_path}")

    # Timeseries — India vs Pakistan military spending
    hist_path = HIST_DIR / "sipri_timeseries.json"
    history   = []
    if hist_path.exists():
        try: history = json.loads(hist_path.read_text(encoding="utf-8"))
        except Exception: history = []

    india_spend = result["military_expenditure"].get("India", {}).get("expenditure_usd", {})
    pak_spend   = result["military_expenditure"].get("Pakistan", {}).get("expenditure_usd", {})
    china_spend = result["military_expenditure"].get("China", {}).get("expenditure_usd", {})

    history.append({
        "date":           now.strftime("%Y-%m-%d"),
        "india_mil_usd":  india_spend.get("value") if india_spend else None,
        "india_data_yr":  india_spend.get("year") if india_spend else None,
        "pak_mil_usd":    pak_spend.get("value") if pak_spend else None,
        "china_mil_usd":  china_spend.get("value") if china_spend else None,
    })
    history = history[-24:]
    hist_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    print(f"History: {hist_path} ({len(history)} entries)")

if __name__ == "__main__":
    main()
