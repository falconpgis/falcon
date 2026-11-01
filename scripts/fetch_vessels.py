"""
FALCON — Engine II: Ocean shipping / vessel traffic near Pakistan/India gateway ports
Source: AIS Hub free API (no key for basic feed) or fallback to static major port data
Monitors: Karachi (Pakistan), JNPT Mumbai, Kandla (India) — Punjab trade gateways

Outputs:
  public/data/vessels.geojson  — vessel positions near gateway ports
  public/data/history/vessels_timeseries.json — daily snapshot counts
"""
import json, datetime, requests
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "public" / "data"
HIST_DIR = DATA_DIR / "history"
HIST_DIR.mkdir(parents=True, exist_ok=True)

# Bounding box: Karachi to JNPT (captures Punjab gateway shipping lanes)
# lat 20.0–26.0, lon 60.0–73.5
LAT_MIN, LAT_MAX = 20.0, 26.0
LON_MIN, LON_MAX = 60.0, 73.5

# Major gateway ports for Punjab trade
GATEWAY_PORTS = [
    {"name": "Karachi Port",  "lon": 66.990, "lat": 24.856, "country": "Pakistan", "type": "major"},
    {"name": "Port Qasim",    "lon": 67.310, "lat": 24.774, "country": "Pakistan", "type": "major"},
    {"name": "Gwadar Port",   "lon": 62.325, "lat": 25.122, "country": "Pakistan", "type": "CPEC"},
    {"name": "JNPT Mumbai",   "lon": 72.954, "lat": 18.948, "country": "India",    "type": "major"},
    {"name": "Kandla Port",   "lon": 70.218, "lat": 23.000, "country": "India",    "type": "major"},
    {"name": "Mundra Port",   "lon": 69.708, "lat": 22.839, "country": "India",    "type": "major"},
]

AISHUB_URL = "https://data.aishub.net/ws.php"

def fetch_aishub():
    """Attempt AIS Hub free feed — returns list of vessel dicts."""
    try:
        params = {
            "username": "AH_ANON_1",  # anonymous tier
            "format": "1",
            "output": "json",
            "latmin": LAT_MIN, "latmax": LAT_MAX,
            "lonmin": LON_MIN, "lonmax": LON_MAX,
        }
        r = requests.get(AISHUB_URL, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and len(data) > 1:
            return data[1]  # AIS Hub format: [metadata, [vessels...]]
        return []
    except Exception as e:
        print(f"[warn] AIS Hub fetch failed: {e}")
        return []

def vessels_to_geojson(vessels, ports):
    """Convert AIS vessel list + static port data to GeoJSON."""
    features = []
    now_str = datetime.datetime.utcnow().isoformat() + "Z"

    # Add static port markers
    for p in ports:
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
            "properties": {
                "name":    p["name"],
                "country": p["country"],
                "type":    "port",
                "port_type": p["type"],
                "date":    now_str,
                "source":  "static",
            },
        })

    # Add live vessels from AIS Hub
    for v in vessels:
        try:
            lon    = float(v.get("LONGITUDE", 0))
            lat    = float(v.get("LATITUDE", 0))
            name   = v.get("NAME", "Unknown").strip()
            mmsi   = v.get("MMSI", "")
            speed  = float(v.get("SPEED", 0))
            course = float(v.get("COURSE", 0))
            vtype  = v.get("TYPE_AND_CARGO", "")

            if lon == 0 and lat == 0:
                continue

            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "name":    name,
                    "mmsi":    mmsi,
                    "speed_kts": round(speed * 0.1, 1),  # AIS speed in 0.1 knot units
                    "course":  round(course * 0.1),
                    "type":    "vessel",
                    "cargo_type": vtype,
                    "date":    now_str,
                    "source":  "AIS Hub",
                },
            })
        except (KeyError, ValueError, TypeError):
            continue

    return {"type": "FeatureCollection", "features": features}

def main():
    print("FALCON · fetch_vessels.py")
    now = datetime.datetime.utcnow()

    vessels = fetch_aishub()
    print(f"[aishub] {len(vessels)} vessels in monitoring zone")

    geo = vessels_to_geojson(vessels, GATEWAY_PORTS)
    vessel_count = sum(1 for f in geo["features"] if f["properties"].get("type") == "vessel")

    out_path = DATA_DIR / "vessels.geojson"
    out_path.write_text(json.dumps(geo, indent=2), encoding="utf-8")
    print(f"Written: {out_path} ({vessel_count} vessels + {len(GATEWAY_PORTS)} ports)")

    # Timeseries
    hist_path = HIST_DIR / "vessels_timeseries.json"
    history = []
    if hist_path.exists():
        try:
            history = json.loads(hist_path.read_text(encoding="utf-8"))
        except Exception:
            history = []

    history.append({
        "date":          now.strftime("%Y-%m-%d"),
        "vessel_count":  vessel_count,
    })
    history = history[-60:]  # 2 months of daily snapshots
    hist_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    print(f"History: {hist_path} ({len(history)} entries)")

if __name__ == "__main__":
    main()
