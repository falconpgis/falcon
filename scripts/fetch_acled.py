"""
FALCON — Engine III: ACLED conflict event fetcher
Auth: OAuth (email + password → Bearer token, 24h validity)
Docs: https://acleddata.com/api-documentation/getting-started

Pulls conflict, protest, and strategic development events for:
  - Punjab, India (state-level filter)
  - Pakistan border regions (Punjab PK, KPK, Balochistan)
  - India-Pakistan border zone (bounding box)
  - Canada-India diplomatic incidents (country-level, keyword filter)

Writes:
  public/data/punjab_events.geojson   — map layer for CesiumJS
  public/data/acled_summary.json      — summary stats for dashboard
  public/data/history/acled_timeseries.json — monthly event counts
"""

import os, json, datetime, requests
from pathlib import Path

EMAIL    = os.environ.get("ACLED_EMAIL", "")
PASSWORD = os.environ.get("ACLED_PASSWORD", "")
BASE     = "https://acleddata.com"
DATA_DIR = Path(__file__).parent.parent / "public" / "data"
HIST_DIR = DATA_DIR / "history"
HIST_DIR.mkdir(parents=True, exist_ok=True)

# Punjab bounding box (India)
BBOX = {"lat_min": 29.5, "lat_max": 32.5, "lon_min": 73.8, "lon_max": 76.9}

def get_token():
    """OAuth login → Bearer token."""
    if not EMAIL or not PASSWORD:
        print("[skip] ACLED_EMAIL or ACLED_PASSWORD not set")
        return None
    r = requests.post(
        f"{BASE}/oauth/token",
        data={
            "username":   EMAIL,
            "password":   PASSWORD,
            "grant_type": "password",
            "client_id":  "acled",
            "scope":      "authenticated",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=20,
    )
    r.raise_for_status()
    token = r.json().get("access_token")
    print(f"[auth] token obtained (expires 24h)")
    return token

def acled_get(token, params, max_rows=500):
    """GET /api/acled/read with Bearer auth. Returns list of event dicts."""
    if not token:
        return []
    headers = {"Authorization": f"Bearer {token}"}
    params  = {**params, "limit": max_rows, "_format": "json"}
    r = requests.get(f"{BASE}/api/acled/read", headers=headers, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("data", [])

def fetch_punjab_india(token):
    """All events in Punjab, India — last 12 months."""
    since = (datetime.datetime.utcnow() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
    rows  = acled_get(token, {
        "country":       "India",
        "admin1":        "Punjab",
        "event_date":    since,
        "event_date_where": "BETWEEN",
        "event_date2":   datetime.datetime.utcnow().strftime("%Y-%m-%d"),
    })
    print(f"  Punjab India: {len(rows)} events")
    return rows

def fetch_border_zone(token):
    """Events within Punjab bounding box — catches cross-border incidents."""
    since = (datetime.datetime.utcnow() - datetime.timedelta(days=180)).strftime("%Y-%m-%d")
    rows  = acled_get(token, {
        "latitude":      BBOX["lat_min"],
        "latitude_where": "BETWEEN",
        "latitude2":     BBOX["lat_max"],
        "longitude":     BBOX["lon_min"],
        "longitude_where": "BETWEEN",
        "longitude2":    BBOX["lon_max"],
        "event_date":    since,
        "event_date_where": "BETWEEN",
        "event_date2":   datetime.datetime.utcnow().strftime("%Y-%m-%d"),
    }, max_rows=300)
    print(f"  Bounding box: {len(rows)} events")
    return rows

def fetch_pakistan_border(token):
    """Pakistan Punjab + Sindh — India-facing border tension signal."""
    since = (datetime.datetime.utcnow() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
    rows  = acled_get(token, {
        "country":    "Pakistan",
        "admin1":     "Punjab",
        "event_date": since,
        "event_date_where": "BETWEEN",
        "event_date2": datetime.datetime.utcnow().strftime("%Y-%m-%d"),
    }, max_rows=200)
    print(f"  Pakistan Punjab: {len(rows)} events")
    return rows

def fetch_sikh_diaspora_incidents(token):
    """
    Canada & UK events mentioning Sikh/Punjabi — diaspora corridor risk signal.
    ACLED covers protests, diplomatic incidents, strategic developments.
    """
    since = (datetime.datetime.utcnow() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
    rows_ca = acled_get(token, {
        "country":    "Canada",
        "event_date": since,
        "event_date_where": "BETWEEN",
        "event_date2": datetime.datetime.utcnow().strftime("%Y-%m-%d"),
        "actor1":     "Sikh",
    }, max_rows=100)
    rows_uk = acled_get(token, {
        "country":    "United Kingdom",
        "event_date": since,
        "event_date_where": "BETWEEN",
        "event_date2": datetime.datetime.utcnow().strftime("%Y-%m-%d"),
        "actor1":     "Sikh",
    }, max_rows=100)
    print(f"  Sikh diaspora incidents: CA={len(rows_ca)} UK={len(rows_uk)}")
    return rows_ca + rows_uk

def events_to_geojson(all_events):
    """Convert ACLED rows → GeoJSON FeatureCollection for CesiumJS map layer."""
    features = []
    seen = set()
    for e in all_events:
        eid = e.get("event_id_cnty") or e.get("data_id")
        if eid in seen:
            continue
        seen.add(eid)
        try:
            lat = float(e.get("latitude",  0))
            lon = float(e.get("longitude", 0))
        except (TypeError, ValueError):
            continue
        if lat == 0 and lon == 0:
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "id":         eid,
                "date":       e.get("event_date"),
                "type":       e.get("event_type"),
                "sub_type":   e.get("sub_event_type"),
                "country":    e.get("country"),
                "admin1":     e.get("admin1"),
                "location":   e.get("location"),
                "actor1":     e.get("actor1"),
                "actor2":     e.get("actor2"),
                "fatalities": int(e.get("fatalities") or 0),
                "notes":      (e.get("notes") or "")[:300],
                "source":     "ACLED",
            },
        })
    return {"type": "FeatureCollection", "features": features}

def summarise(all_events):
    """Compute summary stats for dashboard."""
    now = datetime.datetime.utcnow()
    last30 = (now - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    last90 = (now - datetime.timedelta(days=90)).strftime("%Y-%m-%d")

    def count_since(cutoff):
        return sum(1 for e in all_events if (e.get("event_date") or "") >= cutoff)

    def fatal_since(cutoff):
        return sum(int(e.get("fatalities") or 0) for e in all_events if (e.get("event_date") or "") >= cutoff)

    # Event type breakdown
    type_counts = {}
    for e in all_events:
        t = e.get("event_type", "Unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    # Monthly counts for timeseries
    monthly = {}
    for e in all_events:
        d = (e.get("event_date") or "")[:7]  # YYYY-MM
        if d:
            monthly[d] = monthly.get(d, 0) + 1

    # Hotspot locations (top 5 by event count)
    locs = {}
    for e in all_events:
        loc = f"{e.get('location','?')}, {e.get('admin1','?')}, {e.get('country','?')}"
        locs[loc] = locs.get(loc, 0) + 1
    hotspots = sorted(locs.items(), key=lambda x: -x[1])[:5]

    return {
        "fetched_utc":       now.isoformat() + "Z",
        "total_events":      len(all_events),
        "events_last_30d":   count_since(last30),
        "events_last_90d":   count_since(last90),
        "fatalities_30d":    fatal_since(last30),
        "fatalities_90d":    fatal_since(last90),
        "event_type_counts": type_counts,
        "monthly_counts":    dict(sorted(monthly.items())),
        "hotspots":          [{"location": loc, "count": cnt} for loc, cnt in hotspots],
    }

def main():
    print("FALCON · fetch_acled.py")

    token = get_token()
    if not token:
        print("[abort] no auth token")
        return

    punjab_in  = fetch_punjab_india(token)
    border     = fetch_border_zone(token)
    pakistan   = fetch_pakistan_border(token)
    diaspora   = fetch_sikh_diaspora_incidents(token)

    all_events = punjab_in + border + pakistan + diaspora

    # Deduplicate by event_id
    seen = set()
    unique = []
    for e in all_events:
        eid = e.get("event_id_cnty") or e.get("data_id") or id(e)
        if eid not in seen:
            seen.add(eid)
            unique.append(e)
    print(f"\nTotal unique events: {len(unique)}")

    # Write GeoJSON map layer
    geo_path = DATA_DIR / "punjab_events.geojson"
    geo_path.write_text(json.dumps(events_to_geojson(unique), indent=2), encoding="utf-8")
    print(f"Written: {geo_path}")

    # Write summary
    summary = summarise(unique)
    sum_path = DATA_DIR / "acled_summary.json"
    sum_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Written: {sum_path}")

    # Append monthly to history
    hist_path = HIST_DIR / "acled_timeseries.json"
    history = []
    if hist_path.exists():
        try:
            history = json.loads(hist_path.read_text(encoding="utf-8"))
        except Exception:
            history = []
    history.append({
        "snapshot_date":   datetime.datetime.utcnow().strftime("%Y-%m-%d"),
        "monthly_counts":  summary["monthly_counts"],
        "total_30d":       summary["events_last_30d"],
        "fatalities_30d":  summary["fatalities_30d"],
    })
    history = history[-24:]  # 2 years of monthly snapshots
    hist_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    print(f"History: {hist_path} ({len(history)} entries)")

    print(f"\n── Summary ──")
    print(f"  Events last 30d: {summary['events_last_30d']}")
    print(f"  Events last 90d: {summary['events_last_90d']}")
    print(f"  Fatalities 30d:  {summary['fatalities_30d']}")
    for t, c in summary["event_type_counts"].items():
        print(f"  {t}: {c}")

if __name__ == "__main__":
    main()
