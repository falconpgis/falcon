"""
FALCON — Engine IV + V: World Bank open indicators
Source: World Bank Data API v2 (free, no key)
Covers: India Punjab-relevant national indicators + Pakistan + diaspora countries

Outputs:
  public/data/worldbank_indicators.json
  public/data/history/worldbank_timeseries.json
"""
import json, datetime, requests
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "public" / "data"
HIST_DIR = DATA_DIR / "history"
HIST_DIR.mkdir(parents=True, exist_ok=True)

WB_URL = "https://api.worldbank.org/v2/country/{country}/indicator/{indicator}?format=json&mrv=5&per_page=5"

# Countries relevant to FALCON
COUNTRIES = {
    "IN": "India",
    "PK": "Pakistan",
    "CN": "China",
    "RU": "Russia",
    "IR": "Iran",
    "AF": "Afghanistan",
    "CA": "Canada",    # Sikh diaspora
    "GB": "UK",        # Sikh diaspora
    "AE": "UAE",       # Sikh diaspora Gulf
    "KZ": "Kazakhstan",
    "UZ": "Uzbekistan",
}

# Indicators most relevant to FALCON's mission
INDICATORS = {
    "NY.GDP.MKTP.CD":    "GDP (current USD)",
    "NY.GDP.PCAP.CD":    "GDP per capita (USD)",
    "FP.CPI.TOTL.ZG":    "Inflation rate (%)",
    "SL.UEM.TOTL.ZS":    "Unemployment rate (%)",
    "SP.POP.TOTL":        "Population",
    "AG.LND.AGRI.ZS":    "Agricultural land (% of land)",
    "ER.H2O.FWST.ZS":    "Water stress level (%)",
    "EN.ATM.PM25.MC.M3": "PM2.5 air pollution (mcg/m3)",
    "SI.POV.NAHC":        "Poverty headcount (%)",
    "BX.TRF.PWKR.CD.DT": "Personal remittances received (USD)",
    "MS.MIL.XPND.GD.ZS": "Military expenditure (% of GDP)",
    "DT.ODA.ODAT.GN.ZS": "Foreign aid received (% of GNI)",
}

def fetch_indicator(country_code, indicator_code):
    url = WB_URL.format(country=country_code, indicator=indicator_code)
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and len(data) > 1:
            entries = data[1] or []
            # Return most recent non-null value
            for e in entries:
                if e.get("value") is not None:
                    return {"year": e["date"], "value": round(float(e["value"]), 3)}
        return None
    except Exception:
        return None

def main():
    print("FALCON · fetch_worldbank.py")
    now = datetime.datetime.utcnow()

    result = {
        "generated_at": now.isoformat() + "Z",
        "source": "World Bank Open Data API",
        "countries": {},
    }

    for code, name in COUNTRIES.items():
        result["countries"][name] = {"code": code, "indicators": {}}
        for ind_code, ind_name in INDICATORS.items():
            val = fetch_indicator(code, ind_code)
            if val:
                result["countries"][name]["indicators"][ind_name] = val
        filled = len(result["countries"][name]["indicators"])
        print(f"  {name:15} {filled}/{len(INDICATORS)} indicators")

    out_path = DATA_DIR / "worldbank_indicators.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Written: {out_path}")

    # Timeseries snapshot of key India indicators
    india = result["countries"].get("India", {}).get("indicators", {})
    hist_path = HIST_DIR / "worldbank_timeseries.json"
    history   = []
    if hist_path.exists():
        try: history = json.loads(hist_path.read_text(encoding="utf-8"))
        except Exception: history = []

    history.append({
        "date":      now.strftime("%Y-%m-%d"),
        "india_gdp": india.get("GDP (current USD)", {}).get("value"),
        "india_inflation": india.get("Inflation rate (%)", {}).get("value"),
        "india_pm25": india.get("PM2.5 air pollution (mcg/m3)", {}).get("value"),
        "india_water_stress": india.get("Water stress level (%)", {}).get("value"),
        "pk_military_pct": result["countries"].get("Pakistan", {})
                           .get("indicators", {}).get("Military expenditure (% of GDP)", {}).get("value"),
    })
    history = history[-24:]  # 2 years of monthly snapshots
    hist_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    print(f"History: {hist_path} ({len(history)} entries)")

if __name__ == "__main__":
    main()
