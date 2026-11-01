"""
FALCON — Engine V: Diaspora — Gurdwara + Sikh MPs fetcher
Sources:
  1. OpenStreetMap Overpass API (free, no key) — Sikh places of worship globally
  2. Wikidata SPARQL (free, no key) — Sikh politicians by country

Outputs:
  public/data/gurdwaras.geojson       — global gurdwara locations for globe layer
  public/data/sikh_mps.json           — Sikh MPs/politicians by country
  public/data/diaspora_summary.json   — country-level diaspora density summary
"""
import json, datetime, requests
from pathlib import Path
from collections import Counter

DATA_DIR = Path(__file__).parent.parent / "public" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

OVERPASS = "https://overpass-api.de/api/interpreter"
WIKIDATA = "https://query.wikidata.org/sparql"

def fetch_gurdwaras_osm():
    """Query Overpass for all Sikh places of worship globally."""
    query = """
[out:json][timeout:120];
(
  node["religion"="sikh"]["amenity"="place_of_worship"];
  way["religion"="sikh"]["amenity"="place_of_worship"];
  relation["religion"="sikh"]["amenity"="place_of_worship"];
);
out center tags 5000;
"""
    print("[OSM] querying Overpass for gurdwaras…")
    r = requests.post(OVERPASS, data={"data": query}, timeout=130)
    r.raise_for_status()
    elements = r.json().get("elements", [])
    print(f"  OSM returned {len(elements)} elements")

    features = []
    for el in elements:
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        if not lat or not lon:
            continue
        tags = el.get("tags", {})
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "id":       str(el.get("id")),
                "name":     tags.get("name") or tags.get("name:en") or "Gurdwara",
                "name_pa":  tags.get("name:pa"),
                "country":  tags.get("addr:country"),
                "city":     tags.get("addr:city"),
                "street":   tags.get("addr:street"),
                "source":   "OpenStreetMap",
            },
        })
    return {"type": "FeatureCollection", "features": features}

def fetch_sikh_mps_wikidata():
    """SPARQL query for Sikh politicians by country."""
    sparql = """
SELECT ?person ?personLabel ?countryLabel ?positionLabel ?partyLabel WHERE {
  ?person wdt:P140 wd:Q9316;        # religion = Sikhism
          wdt:P39 ?position.         # holds position
  ?position wdt:P17 ?country.
  OPTIONAL { ?person wdt:P102 ?party. }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 500
"""
    headers = {"Accept": "application/sparql-results+json", "User-Agent": "FALCON-PGIS/1.0"}
    print("[Wikidata] querying Sikh politicians…")
    r = requests.get(WIKIDATA, params={"query": sparql, "format": "json"},
                     headers=headers, timeout=60)
    r.raise_for_status()
    bindings = r.json().get("results", {}).get("bindings", [])
    print(f"  Wikidata returned {len(bindings)} results")

    mps = []
    for b in bindings:
        mps.append({
            "name":     b.get("personLabel",   {}).get("value",""),
            "country":  b.get("countryLabel",  {}).get("value",""),
            "position": b.get("positionLabel", {}).get("value",""),
            "party":    b.get("partyLabel",    {}).get("value",""),
            "wikidata": b.get("person",        {}).get("value",""),
        })
    return mps

def summarise(geojson, mps):
    """Country-level diaspora density summary."""
    country_gurdwaras = Counter()
    for f in geojson.get("features", []):
        c = f["properties"].get("country") or "Unknown"
        country_gurdwaras[c] += 1

    country_mps = Counter(m["country"] for m in mps if m["country"])

    all_countries = set(country_gurdwaras) | set(country_mps)
    rows = []
    for c in sorted(all_countries):
        rows.append({
            "country":    c,
            "gurdwaras":  country_gurdwaras.get(c, 0),
            "sikh_mps":   country_mps.get(c, 0),
        })
    rows.sort(key=lambda x: -(x["gurdwaras"] + x["sikh_mps"] * 10))
    return rows

def main():
    print("FALCON · fetch_gurdwaras.py")
    now = datetime.datetime.utcnow()

    geo = {"type": "FeatureCollection", "features": []}
    try:
        geo = fetch_gurdwaras_osm()
    except Exception as e:
        print(f"[warn] OSM failed: {e}")

    mps = []
    try:
        mps = fetch_sikh_mps_wikidata()
    except Exception as e:
        print(f"[warn] Wikidata failed: {e}")

    # Write GeoJSON
    geo_path = DATA_DIR / "gurdwaras.geojson"
    geo_path.write_text(json.dumps(geo, indent=2), encoding="utf-8")
    print(f"Written: {geo_path}  ({len(geo['features'])} features)")

    # Write MPs
    mps_path = DATA_DIR / "sikh_mps.json"
    mps_path.write_text(json.dumps({
        "fetched_utc": now.isoformat() + "Z",
        "total": len(mps),
        "politicians": mps,
    }, indent=2), encoding="utf-8")
    print(f"Written: {mps_path}")

    # Write summary
    summary = summarise(geo, mps)
    sum_path = DATA_DIR / "diaspora_summary.json"
    sum_path.write_text(json.dumps({
        "fetched_utc": now.isoformat() + "Z",
        "total_gurdwaras": len(geo["features"]),
        "total_sikh_politicians": len(mps),
        "by_country": summary,
    }, indent=2), encoding="utf-8")
    print(f"Written: {sum_path}")

    # Print top countries
    for row in summary[:10]:
        print(f"  {row['country']:25s} gurdwaras={row['gurdwaras']:4d}  MPs={row['sikh_mps']}")

if __name__ == "__main__":
    main()
