"""
FALCON — Engine II: Live air traffic over Punjab region
Source: OpenSky Network REST API (free, no key for anonymous)
Punjab bounding box: lat 29.5–32.5, lon 73.8–76.9

Outputs:
  public/data/air_traffic.geojson  — live aircraft positions
  public/data/history/air_traffic_timeseries.json — hourly snapshot counts
"""
import json, datetime, requests
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "public" / "data"
HIST_DIR = DATA_DIR / "history"
HIST_DIR.mkdir(parents=True, exist_ok=True)

# Punjab bounding box
LAT_MIN, LAT_MAX = 29.5, 32.5
LON_MIN, LON_MAX = 73.8, 76.9

OPENSKY_URL = "https://opensky-network.org/api/states/all"

def fetch_opensky():
    """Fetch aircraft in Punjab bounding box."""
    params = {
        "lamin": LAT_MIN, "lamax": LAT_MAX,
        "lomin": LON_MIN, "lomax": LON_MAX,
    }
    try:
        r = requests.get(OPENSKY_URL, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        return data.get("states", []) or []
    except Exception as e:
        print(f"[warn] OpenSky fetch failed: {e}")
        return []

def states_to_geojson(states):
    """Convert OpenSky state vectors to GeoJSON."""
    features = []
    now_str = datetime.datetime.utcnow().isoformat() + "Z"

    for s in states:
        # OpenSky state vector fields:
        # 0=icao24, 1=callsign, 2=origin_country, 5=longitude, 6=latitude,
        # 7=baro_altitude(m), 9=velocity(m/s), 10=heading, 13=on_ground
        try:
            icao24    = s[0] or ""
            callsign  = (s[1] or "").strip() or icao24
            country   = s[2] or "Unknown"
            lon       = s[5]
            lat       = s[6]
            alt_m     = s[7]
            speed_ms  = s[9]
            heading   = s[10]
            on_ground = s[8]  # index 8 = on_ground bool

            if lon is None or lat is None:
                continue
            if on_ground:
                continue  # skip parked aircraft

            alt_ft = round(alt_m * 3.28084) if alt_m else 0
            speed_kts = round(speed_ms * 1.94384) if speed_ms else 0

            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "icao24":    icao24,
                    "callsign":  callsign,
                    "country":   country,
                    "altitude_ft": alt_ft,
                    "speed_kts": speed_kts,
                    "heading":   round(heading) if heading else 0,
                    "date":      now_str,
                    "source":    "OpenSky Network",
                },
            })
        except (IndexError, TypeError):
            continue

    return {"type": "FeatureCollection", "features": features}

def main():
    print("FALCON · fetch_air_traffic.py")
    now = datetime.datetime.utcnow()

    states = fetch_opensky()
    print(f"[opensky] {len(states)} aircraft in bounding box")

    geo = states_to_geojson(states)
    out_path = DATA_DIR / "air_traffic.geojson"
    out_path.write_text(json.dumps(geo, indent=2), encoding="utf-8")
    print(f"Written: {out_path} ({len(geo['features'])} airborne aircraft)")

    # Timeseries count
    hist_path = HIST_DIR / "air_traffic_timeseries.json"
    history = []
    if hist_path.exists():
        try:
            history = json.loads(hist_path.read_text(encoding="utf-8"))
        except Exception:
            history = []

    history.append({
        "ts":    now.strftime("%Y-%m-%dT%H:00Z"),
        "count": len(geo["features"]),
    })
    history = history[-168:]  # 7 days of hourly snapshots
    hist_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    print(f"History: {hist_path} ({len(history)} entries)")

if __name__ == "__main__":
    main()
