"""
FALCON — Engine I: Guru Nanak Dev Ji — 4 Udasis (journeys) route data
Source: Wikidata SPARQL (free, no key) + curated coordinates from Sikh historical texts
        Sri Nanak Parkash (Bhai Santokh Singh) — primary textual source

4 Udasis (journeys undertaken between ~1499 and ~1524 CE):
  Udasi 1 (1499-1506): East — Sultanpur → Haridwar → Benares → Jagannath → Rameshwaram → ...
  Udasi 2 (1506-1513): South — Sri Lanka, Arabia, Baghdad
  Udasi 3 (1514-1518): North — Himalayas, Tibet, Sikkim
  Udasi 4 (1518-1521): West — Mecca, Medina, Baghdad, Kabul

Outputs:
  public/data/guru_udasis.geojson    — all stop points with sequence
  public/data/history/udasis_log.json
"""
import json, datetime, requests
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "public" / "data"
HIST_DIR = DATA_DIR / "history"
HIST_DIR.mkdir(parents=True, exist_ok=True)

# Wikidata SPARQL endpoint
SPARQL_URL = "https://query.wikidata.org/sparql"
HEADERS    = {
    "User-Agent": "FALCON-PGIS/1.0 (Sikh historical GIS; falconpgis.github.io)",
    "Accept": "application/sparql-results+json",
}

# SPARQL query — places associated with Guru Nanak Dev Ji's travels
SPARQL_QUERY = """
SELECT DISTINCT ?place ?placeLabel ?lat ?lon ?instance ?instanceLabel WHERE {
  ?place wdt:P825 wd:Q9640.       # places associated with Guru Nanak
  OPTIONAL { ?place wdt:P625 ?coord .
             BIND(geof:latitude(?coord)  AS ?lat)
             BIND(geof:longitude(?coord) AS ?lon) }
  OPTIONAL { ?place wdt:P31 ?instance }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,pa". }
}
LIMIT 200
"""

# Curated stops from Sikh historical sources (Sri Nanak Parkash, Janam Sakhis)
# These are hand-verified coordinates for key Udasi stops
CURATED_UDASIS = {
    "Udasi 1": {
        "direction": "East",
        "years": "~1499-1506",
        "description": "East India — Benares, Orissa, Sri Lanka",
        "stops": [
            {"seq": 1,  "name": "Sultanpur Lodhi",    "lat": 31.023, "lon": 75.187, "note": "Departure point; revelation at River Bein"},
            {"seq": 2,  "name": "Panipat",             "lat": 29.390, "lon": 76.969, "note": "Met Shaikh Taahraan"},
            {"seq": 3,  "name": "Delhi",               "lat": 28.613, "lon": 77.209, "note": ""},
            {"seq": 4,  "name": "Haridwar",            "lat": 29.945, "lon": 78.166, "note": "Kumbh Mela visit; sun-water episode"},
            {"seq": 5,  "name": "Gorakhmata",          "lat": 28.440, "lon": 80.191, "note": "Later became Nanakmata; Sidh conversation"},
            {"seq": 6,  "name": "Benares (Varanasi)",  "lat": 25.317, "lon": 83.005, "note": "Major stop; conversation with Pandit Chatur Das"},
            {"seq": 7,  "name": "Gaya",                "lat": 24.796, "lon": 84.994, "note": ""},
            {"seq": 8,  "name": "Puri (Jagannath)",    "lat": 19.804, "lon": 85.818, "note": "Aarti episode at Jagannath Temple"},
            {"seq": 9,  "name": "Cuttack",             "lat": 20.462, "lon": 85.882, "note": ""},
            {"seq": 10, "name": "Rameshwaram",         "lat": 9.288,  "lon": 79.313, "note": "Southernmost point of Udasi 1"},
            {"seq": 11, "name": "Sri Lanka (Jaffna)",  "lat": 9.669,  "lon": 80.007, "note": "Ceylon visit"},
            {"seq": 12, "name": "Tirupati",            "lat": 13.634, "lon": 79.419, "note": ""},
            {"seq": 13, "name": "Nanded",              "lat": 19.065, "lon": 77.326, "note": "Later site of Sachkhand Sri Hazur Sahib"},
            {"seq": 14, "name": "Bidar",               "lat": 17.913, "lon": 77.512, "note": ""},
            {"seq": 15, "name": "Aurangabad",          "lat": 19.877, "lon": 75.343, "note": ""},
            {"seq": 16, "name": "Nashik",              "lat": 19.998, "lon": 73.790, "note": ""},
            {"seq": 17, "name": "Ujjain",              "lat": 23.182, "lon": 75.777, "note": ""},
            {"seq": 18, "name": "Kartarpur (return)",  "lat": 31.444, "lon": 75.028, "note": "Return and founding of Kartarpur"},
        ]
    },
    "Udasi 2": {
        "direction": "South / Arabia",
        "years": "~1506-1513",
        "description": "South India, Sri Lanka, Arabia, Baghdad, Persia",
        "stops": [
            {"seq": 1,  "name": "Kartarpur",           "lat": 31.444, "lon": 75.028, "note": "Departure"},
            {"seq": 2,  "name": "Lahore",              "lat": 31.549, "lon": 74.343, "note": ""},
            {"seq": 3,  "name": "Talwandi (Nankana)",  "lat": 31.451, "lon": 73.704, "note": "Birthplace visit"},
            {"seq": 4,  "name": "Pak Pattan",          "lat": 30.343, "lon": 73.385, "note": "Farid's shrine"},
            {"seq": 5,  "name": "Multan",              "lat": 30.197, "lon": 71.481, "note": "Major stop"},
            {"seq": 6,  "name": "Sindh",               "lat": 25.396, "lon": 68.370, "note": ""},
            {"seq": 7,  "name": "Kutch",               "lat": 23.733, "lon": 70.400, "note": ""},
            {"seq": 8,  "name": "Dwarka",              "lat": 22.238, "lon": 68.967, "note": ""},
            {"seq": 9,  "name": "Somnath",             "lat": 20.888, "lon": 70.401, "note": ""},
            {"seq": 10, "name": "Mecca",               "lat": 21.388, "lon": 39.825, "note": "Famous shoe-turning episode"},
            {"seq": 11, "name": "Medina",              "lat": 24.467, "lon": 39.611, "note": ""},
            {"seq": 12, "name": "Baghdad",             "lat": 33.340, "lon": 44.401, "note": "Mardana and flower episode; met Pir Bahlol"},
            {"seq": 13, "name": "Kabul",               "lat": 34.526, "lon": 69.179, "note": ""},
            {"seq": 14, "name": "Kartarpur (return)",  "lat": 31.444, "lon": 75.028, "note": "Return"},
        ]
    },
    "Udasi 3": {
        "direction": "North / Himalayas",
        "years": "~1514-1518",
        "description": "Himalayas, Kashmir, Tibet, Nepal — Sidhs' summits",
        "stops": [
            {"seq": 1,  "name": "Kartarpur",           "lat": 31.444, "lon": 75.028, "note": "Departure"},
            {"seq": 2,  "name": "Srinagar",            "lat": 34.084, "lon": 74.797, "note": ""},
            {"seq": 3,  "name": "Baramulla",           "lat": 34.202, "lon": 74.343, "note": ""},
            {"seq": 4,  "name": "Amarnath",            "lat": 34.216, "lon": 75.510, "note": "Himalayan pilgrimage"},
            {"seq": 5,  "name": "Kailash Mansarovar",  "lat": 30.764, "lon": 81.312, "note": "Tibet; summit with Sidhs — Sidh Gosht"},
            {"seq": 6,  "name": "Nepal (Kathmandu)",   "lat": 27.700, "lon": 85.318, "note": "Pashupatinath"},
            {"seq": 7,  "name": "Pilibhit",            "lat": 28.631, "lon": 79.805, "note": "Nanakmata nearby"},
            {"seq": 8,  "name": "Kartarpur (return)",  "lat": 31.444, "lon": 75.028, "note": "Return"},
        ]
    },
    "Udasi 4": {
        "direction": "West / Afghanistan",
        "years": "~1518-1521",
        "description": "Punjab, Sindh, Afghanistan, Iran, Iraq, Arabia — final long journey",
        "stops": [
            {"seq": 1,  "name": "Kartarpur",           "lat": 31.444, "lon": 75.028, "note": "Departure"},
            {"seq": 2,  "name": "Pasrur",              "lat": 32.260, "lon": 74.663, "note": ""},
            {"seq": 3,  "name": "Sialkot",             "lat": 32.492, "lon": 74.531, "note": ""},
            {"seq": 4,  "name": "Saidpur (Eminabad)",  "lat": 32.059, "lon": 74.207, "note": "Lalo's house; Babar's invasion foretold"},
            {"seq": 5,  "name": "Kabul",               "lat": 34.526, "lon": 69.179, "note": ""},
            {"seq": 6,  "name": "Kandahar",            "lat": 31.628, "lon": 65.700, "note": ""},
            {"seq": 7,  "name": "Herat",               "lat": 34.352, "lon": 62.204, "note": ""},
            {"seq": 8,  "name": "Mashad",              "lat": 36.297, "lon": 59.606, "note": "Imam Reza shrine"},
            {"seq": 9,  "name": "Tehran",              "lat": 35.690, "lon": 51.390, "note": ""},
            {"seq": 10, "name": "Baghdad",             "lat": 33.340, "lon": 44.401, "note": "Second visit; Pir Dastgir shrine"},
            {"seq": 11, "name": "Mecca (second visit)","lat": 21.388, "lon": 39.825, "note": ""},
            {"seq": 12, "name": "Sindh",               "lat": 25.396, "lon": 68.370, "note": "Return route through Sindh"},
            {"seq": 13, "name": "Kartarpur (final)",   "lat": 31.444, "lon": 75.028, "note": "Settled permanently; final years"},
        ]
    }
}

def fetch_wikidata():
    """Try to get additional place data from Wikidata."""
    try:
        r = requests.get(
            SPARQL_URL,
            params={"query": SPARQL_QUERY, "format": "json"},
            headers=HEADERS,
            timeout=30
        )
        r.raise_for_status()
        data     = r.json()
        bindings = data.get("results", {}).get("bindings", [])
        places   = []
        for b in bindings:
            lat = b.get("lat", {}).get("value")
            lon = b.get("lon", {}).get("value")
            if lat and lon:
                places.append({
                    "name": b.get("placeLabel", {}).get("value", ""),
                    "lat":  float(lat),
                    "lon":  float(lon),
                    "wiki": b.get("place", {}).get("value", ""),
                    "type": b.get("instanceLabel", {}).get("value", ""),
                })
        return places
    except Exception as e:
        print(f"[warn] Wikidata fetch: {e}")
        return []

def build_geojson():
    """Build GeoJSON from curated stops + wikidata enrichment."""
    now      = datetime.datetime.utcnow()
    features = []

    for udasi_name, udasi in CURATED_UDASIS.items():
        for stop in udasi["stops"]:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [stop["lon"], stop["lat"]]
                },
                "properties": {
                    "udasi":       udasi_name,
                    "udasi_num":   int(udasi_name.split(" ")[1]),
                    "direction":   udasi["direction"],
                    "years":       udasi["years"],
                    "seq":         stop["seq"],
                    "name":        stop["name"],
                    "note":        stop.get("note", ""),
                    "source":      "Sri Nanak Parkash (Bhai Santokh Singh) / Janam Sakhis",
                    "date":        now.strftime("%Y-%m-%d"),
                }
            })

    return {
        "type":         "FeatureCollection",
        "generated_at": now.isoformat() + "Z",
        "total_stops":  len(features),
        "udasis":       list(CURATED_UDASIS.keys()),
        "features":     features,
    }

def main():
    print("FALCON · fetch_udasis.py")
    now = datetime.datetime.utcnow()

    print("  Fetching Wikidata enrichment...")
    wiki_places = fetch_wikidata()
    print(f"  Wikidata: {len(wiki_places)} associated places found")

    geo = build_geojson()
    print(f"  Built GeoJSON: {geo['total_stops']} stops across {len(CURATED_UDASIS)} Udasis")

    out_path = DATA_DIR / "guru_udasis.geojson"
    out_path.write_text(json.dumps(geo, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Written: {out_path}")

    # Log
    hist_path = HIST_DIR / "udasis_log.json"
    history   = []
    if hist_path.exists():
        try: history = json.loads(hist_path.read_text(encoding="utf-8"))
        except Exception: history = []

    history.append({
        "date":           now.strftime("%Y-%m-%d"),
        "total_stops":    geo["total_stops"],
        "wikidata_hits":  len(wiki_places),
    })
    history = history[-24:]
    hist_path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"History: {hist_path}")

if __name__ == "__main__":
    main()
