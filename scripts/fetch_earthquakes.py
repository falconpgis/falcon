"""
FALCON — Engine II + III: Earthquake monitoring
Source: USGS Earthquake Hazards Program (free, no key)
Zone: Punjab + broader South/Central Asia seismic belt
      lat 25-38, lon 60-85 (covers Hindu Kush, Himalayas, Karakoram)

Outputs:
  public/data/earthquakes.geojson       — events last 30 days, M>=3.0
  public/data/history/earthquakes_timeseries.json — daily count + max magnitude
"""
import json, datetime, requests
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "public" / "data"
HIST_DIR = DATA_DIR / "history"
HIST_DIR.mkdir(parents=True, exist_ok=True)

# Broad South/Central Asia bbox
LAT_MIN, LAT_MAX = 25.0, 38.0
LON_MIN, LON_MAX = 60.0, 85.0
MIN_MAG = 3.0

USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

def fetch_quakes():
    end   = datetime.datetime.utcnow()
    start = end - datetime.timedelta(days=30)
    params = {
        "format":       "geojson",
        "starttime":    start.strftime("%Y-%m-%d"),
        "endtime":      end.strftime("%Y-%m-%d"),
        "minlatitude":  LAT_MIN, "maxlatitude":  LAT_MAX,
        "minlongitude": LON_MIN, "maxlongitude": LON_MAX,
        "minmagnitude": MIN_MAG,
        "orderby":      "time",
        "limit":        500,
    }
    try:
        r = requests.get(USGS_URL, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[warn] USGS fetch failed: {e}")
        return {"type": "FeatureCollection", "features": []}

def enrich(geo):
    """Add engine-relevant tags to each feature."""
    PUNJAB_BOX = (29.5, 32.5, 73.8, 76.9)
    for f in geo.get("features", []):
        coords = f["geometry"]["coordinates"]
        lon, lat = coords[0], coords[1]
        props   = f["properties"]
        mag     = props.get("mag", 0) or 0
        # Tag proximity
        in_punjab = (PUNJAB_BOX[0] <= lat <= PUNJAB_BOX[1] and
                     PUNJAB_BOX[2] <= lon <= PUNJAB_BOX[3])
        props["near_punjab"] = in_punjab
        props["alert_level"] = (
            "major"    if mag >= 6.0 else
            "moderate" if mag >= 5.0 else
            "minor"    if mag >= 4.0 else
            "micro"
        )
        props["source"] = "USGS"
    return geo

def main():
    print("FALCON · fetch_earthquakes.py")
    now = datetime.datetime.utcnow()

    geo = fetch_quakes()
    geo = enrich(geo)
    count = len(geo.get("features", []))
    print(f"[usgs] {count} earthquakes M>={MIN_MAG} in zone (last 30 days)")

    out = DATA_DIR / "earthquakes.geojson"
    out.write_text(json.dumps(geo, indent=2), encoding="utf-8")
    print(f"Written: {out}")

    # Timeseries
    mags = [f["properties"].get("mag", 0) or 0 for f in geo.get("features", [])]
    hist_path = HIST_DIR / "earthquakes_timeseries.json"
    history   = []
    if hist_path.exists():
        try: history = json.loads(hist_path.read_text(encoding="utf-8"))
        except Exception: history = []

    history.append({
        "date":    now.strftime("%Y-%m-%d"),
        "count":   count,
        "max_mag": round(max(mags), 1) if mags else 0,
    })
    history = history[-90:]
    hist_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    print(f"History: {hist_path} ({len(history)} entries)")

if __name__ == "__main__":
    main()
