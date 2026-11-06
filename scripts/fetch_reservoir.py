"""
FALCON — Engine II: Water reservoir and canal levels — Punjab water security
Source: Central Water Commission India (cwc.gov.in) — public data
        + Bhakra Beas Management Board reservoirs (critical for Punjab)

Key reservoirs for Punjab:
  - Bhakra (Gobind Sagar) — largest, feeds all Punjab canals
  - Pong Dam (Maharana Pratap Sagar) — Beas river
  - Ranjit Sagar Dam — Ravi river
  - Thein Dam — Ravi river

Outputs:
  public/data/punjab_reservoirs.json
  public/data/history/reservoir_timeseries.json
"""
import json, datetime, requests
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "public" / "data"
HIST_DIR = DATA_DIR / "history"
HIST_DIR.mkdir(parents=True, exist_ok=True)

# CWC daily reservoir bulletin API
CWC_URL   = "https://cwc.gov.in/sites/default/files/resbull.json"
CWC_ALT   = "https://indiawris.gov.in/wris/#/reservoirStorages"

# Bhakra BBMB API (Central Govt data portal)
DATA_GOV_URL = "https://data.gov.in/resource/daily-reservoir-storage-data"

# Key Punjab / North India reservoir identifiers
PUNJAB_RESERVOIRS = {
    "Gobind Sagar (Bhakra)": {
        "river": "Sutlej", "state": "Himachal Pradesh",
        "frl_mcm": 7501.4, "lat": 31.41, "lon": 76.43,
        "cwc_id": "BHAKRA",
    },
    "Pong Dam": {
        "river": "Beas", "state": "Himachal Pradesh",
        "frl_mcm": 8570.0, "lat": 32.00, "lon": 75.93,
        "cwc_id": "PONG",
    },
    "Ranjit Sagar Dam": {
        "river": "Ravi", "state": "Jammu & Kashmir",
        "frl_mcm": 3280.0, "lat": 32.56, "lon": 75.67,
        "cwc_id": "RANJITSAGAR",
    },
    "Thein (Ranjit Sagar)": {
        "river": "Ravi", "state": "Punjab",
        "frl_mcm": 3280.0, "lat": 32.49, "lon": 75.74,
        "cwc_id": "THEIN",
    },
}

def fetch_cwc():
    """Try CWC daily bulletin JSON."""
    try:
        r = requests.get(CWC_URL, timeout=20, headers={"User-Agent": "FALCON-PGIS/1.0"})
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[warn] CWC direct fetch failed: {e}")
        return None

def fetch_data_gov():
    """Try data.gov.in reservoir storage API."""
    try:
        url = "https://api.data.gov.in/resource/50f9f3a1-72ae-4bdb-be38-0a800a66a2f9"
        params = {
            "api-key": "579b464db66ec23bdd000001cdd3946e44ce4aab0ddc2e5df1875f3",  # public demo key
            "format":  "json",
            "limit":   50,
            "filters[State]": "Punjab",
        }
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[warn] data.gov.in fetch failed: {e}")
        return None

def build_fallback():
    """Static fallback with seasonal typical values."""
    now = datetime.datetime.utcnow()
    month = now.month
    # Approximate % full by month (pre-monsoon low Jun, post-monsoon high Oct)
    typical = {1:65,2:58,3:50,4:42,5:35,6:28,7:40,8:62,9:80,10:88,11:80,12:72}
    pct = typical.get(month, 60)
    result = {}
    for name, meta in PUNJAB_RESERVOIRS.items():
        storage_mcm = round(meta["frl_mcm"] * pct / 100, 1)
        result[name] = {
            **meta,
            "storage_mcm": storage_mcm,
            "percent_full": pct,
            "date": now.strftime("%Y-%m-%d"),
            "source": "seasonal-estimate",
            "alert": "low" if pct < 35 else ("critical" if pct < 20 else "normal"),
        }
    return result

def main():
    print("FALCON · fetch_reservoir.py")
    now = datetime.datetime.utcnow()

    # Try live sources, fall back to seasonal estimate
    cwc_data  = fetch_cwc()
    reservoirs = build_fallback()   # always have fallback

    # Try to overlay live data if CWC responded
    if cwc_data:
        print(f"[cwc] Live data available")
        # CWC format varies — attempt to parse standard bulletin format
        try:
            for entry in (cwc_data if isinstance(cwc_data, list) else []):
                name = entry.get("reservoir_name", "") or entry.get("name", "")
                live_storage = entry.get("live_storage_mcm") or entry.get("storage")
                if live_storage and name:
                    for res_name, meta in PUNJAB_RESERVOIRS.items():
                        if meta["cwc_id"].upper() in name.upper() or name.upper() in res_name.upper():
                            pct = round(float(live_storage) / meta["frl_mcm"] * 100, 1)
                            reservoirs[res_name].update({
                                "storage_mcm":  round(float(live_storage), 1),
                                "percent_full": pct,
                                "source": "CWC live",
                                "alert": "low" if pct < 35 else ("critical" if pct < 20 else "normal"),
                            })
        except Exception as e:
            print(f"[warn] CWC parse failed: {e}")

    # Build GeoJSON-like output
    features = []
    for name, data in reservoirs.items():
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [data["lon"], data["lat"]]},
            "properties": {
                "name":         name,
                "river":        data["river"],
                "state":        data["state"],
                "frl_mcm":      data["frl_mcm"],
                "storage_mcm":  data["storage_mcm"],
                "percent_full": data["percent_full"],
                "alert":        data["alert"],
                "source":       data["source"],
                "date":         data["date"],
            }
        })
        print(f"  {name:30} {data['percent_full']:5.1f}% ({data['alert']})")

    out = {
        "type": "FeatureCollection",
        "generated_at": now.isoformat() + "Z",
        "features": features,
    }
    out_path = DATA_DIR / "punjab_reservoirs.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Written: {out_path}")

    # Timeseries
    hist_path = HIST_DIR / "reservoir_timeseries.json"
    history   = []
    if hist_path.exists():
        try: history = json.loads(hist_path.read_text(encoding="utf-8"))
        except Exception: history = []

    history.append({
        "date": now.strftime("%Y-%m-%d"),
        **{name.split("(")[0].strip(): data["percent_full"]
           for name, data in reservoirs.items()},
    })
    history = history[-365:]
    hist_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    print(f"History: {hist_path} ({len(history)} entries)")

if __name__ == "__main__":
    main()
