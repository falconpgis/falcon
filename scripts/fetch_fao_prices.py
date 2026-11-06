"""
FALCON — Engine II + IV: FAO Food Price Index + commodity prices
Source: FAO FAOSTAT Data API (free, no key required)
        FAO Food Price Index (FFPI) — monthly global benchmark

Key commodities for Punjab:
  Wheat, Rice, Maize, Sugar, Vegetable Oils, Dairy

Outputs:
  public/data/fao_prices.json
  public/data/history/fao_timeseries.json
"""
import json, datetime, requests
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "public" / "data"
HIST_DIR = DATA_DIR / "history"
HIST_DIR.mkdir(parents=True, exist_ok=True)

# FAO Food Price Index API
FAO_FFPI_URL = "https://www.fao.org/giews/food-prices/food-info/en/"

# FAO FAOSTAT API — Food Price Index data
FAOSTAT_URL = "https://fenixservices.fao.org/faostat/api/v1/en/data/CPFS"

# World Bank commodity prices (simpler, same data)
WB_COMMODITY_URL = "https://api.worldbank.org/v2/en/indicator/{ind}?downloadformat=json&mrv=12&per_page=12&format=json"

# Commodity indicators from World Bank (align with Punjab farm economy)
COMMODITIES = {
    "Wheat ($/mt)":          "PWHEAMT",   # wheat price
    "Rice ($/mt)":           "PRICENPQ",  # rice price
    "Cotton ($/kg)":         "PCOTTIND",  # cotton
    "Sugar ($/kg)":          "PSUGAUSA",  # sugar
    "Maize ($/mt)":          "PMAIZMMT",  # maize
    "Palm Oil ($/mt)":       "PPOILUSD",  # vegetable oil
    "Natural Gas ($/mmbtu)": "PNGASEU",   # energy for pumps
    "Fertilizer Urea ($/mt)":"PUREA",     # farm input cost
    "Diesel ($/bbl)":        "POILBRE",   # crude oil proxy
}

def fetch_wb_commodity(indicator):
    url = f"https://api.worldbank.org/v2/country/WLD/indicator/{indicator}?format=json&mrv=12&per_page=12"
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and len(data) > 1:
            entries = [e for e in (data[1] or []) if e.get("value") is not None]
            entries.sort(key=lambda x: x["date"], reverse=True)
            if entries:
                latest = entries[0]
                history_vals = [
                    {"date": e["date"], "value": round(float(e["value"]), 2)}
                    for e in entries[:12]
                ]
                return {
                    "latest_value": round(float(latest["value"]), 2),
                    "latest_date":  latest["date"],
                    "history":      history_vals,
                }
        return None
    except Exception as e:
        print(f"[warn] WB commodity {indicator}: {e}")
        return None

def fetch_fao_ffpi():
    """Fetch FAO Food Price Index via their public CSV."""
    try:
        # FAO FFPI public data
        url = "https://www.fao.org/giews/food-prices/tool/public_html/fpi_csv_en.csv"
        r   = requests.get(url, timeout=20)
        r.raise_for_status()
        lines   = r.text.strip().split("\n")
        headers = [h.strip().strip('"') for h in lines[0].split(",")]
        entries = []
        for line in lines[1:]:
            vals = [v.strip().strip('"') for v in line.split(",")]
            if len(vals) >= len(headers):
                entry = dict(zip(headers, vals))
                entries.append(entry)
        # Return last 6 months
        return entries[-6:] if entries else []
    except Exception as e:
        print(f"[warn] FAO FFPI fetch failed: {e}")
        return []

def main():
    print("FALCON · fetch_fao_prices.py")
    now = datetime.datetime.utcnow()

    result = {
        "generated_at": now.isoformat() + "Z",
        "source":        "World Bank Commodity Markets + FAO",
        "note":          "Prices in USD. Wheat/Rice/Fertilizer most relevant to Punjab farm economy.",
        "commodities":   {},
        "fao_ffpi":      [],
    }

    for name, indicator in COMMODITIES.items():
        data = fetch_wb_commodity(indicator)
        if data:
            result["commodities"][name] = data
            print(f"  {name:30} {data['latest_value']:10.2f} ({data['latest_date']})")
        else:
            print(f"  {name:30} — no data")

    ffpi = fetch_fao_ffpi()
    result["fao_ffpi"] = ffpi
    if ffpi:
        print(f"  FAO FFPI: {len(ffpi)} months")

    out_path = DATA_DIR / "fao_prices.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Written: {out_path}")

    # Timeseries — wheat and rice as key Punjab signals
    hist_path = HIST_DIR / "fao_timeseries.json"
    history   = []
    if hist_path.exists():
        try: history = json.loads(hist_path.read_text(encoding="utf-8"))
        except Exception: history = []

    wheat = result["commodities"].get("Wheat ($/mt)", {})
    rice  = result["commodities"].get("Rice ($/mt)", {})
    urea  = result["commodities"].get("Fertilizer Urea ($/mt)", {})
    history.append({
        "date":       now.strftime("%Y-%m-%d"),
        "wheat_usd":  wheat.get("latest_value"),
        "rice_usd":   rice.get("latest_value"),
        "urea_usd":   urea.get("latest_value"),
    })
    history = history[-24:]
    hist_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    print(f"History: {hist_path} ({len(history)} entries)")

if __name__ == "__main__":
    main()
