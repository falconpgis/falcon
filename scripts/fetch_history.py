"""
FALCON — Engine I: History — Anglo-Sikh Wars + Sikh Empire layers
Source: Wikidata SPARQL (free, no key required)
Run once; output is static GeoJSON committed to repo.

Outputs:
  public/data/punjab_historical/anglo_sikh_wars.geojson  — battle sites
  public/data/punjab_historical/misl_capitals.geojson    — 12 Misls capitals
  public/data/punjab_historical/sikh_sites.geojson       — key historical sites
"""
import json, datetime, requests
from pathlib import Path

HIST_DIR = Path(__file__).parent.parent / "public" / "data" / "punjab_historical"
HIST_DIR.mkdir(parents=True, exist_ok=True)

WIKIDATA = "https://query.wikidata.org/sparql"
HEADERS  = {"Accept": "application/sparql-results+json",
             "User-Agent": "FALCON-PGIS/1.0 (historical data pipeline)"}

def sparql(query):
    r = requests.get(WIKIDATA, params={"query": query, "format": "json"},
                     headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r.json().get("results", {}).get("bindings", [])

def fetch_anglo_sikh_wars():
    """Anglo-Sikh War battles with coordinates, date, outcome."""
    q = """
SELECT ?battle ?battleLabel ?date ?lon ?lat ?outcome ?outcomeLabel WHERE {
  VALUES ?war { wd:Q1197487 wd:Q1197499 }   # First + Second Anglo-Sikh War
  ?battle wdt:P361 ?war;
          wdt:P625 ?coord.
  BIND(geof:longitude(?coord) AS ?lon)
  BIND(geof:latitude(?coord)  AS ?lat)
  OPTIONAL { ?battle wdt:P585 ?date. }
  OPTIONAL { ?battle wdt:P793 ?outcome. }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,pa". }
}
"""
    print("[Wikidata] Anglo-Sikh Wars battles…")
    rows = sparql(q)
    print(f"  {len(rows)} rows")

    features = []
    seen = set()
    for b in rows:
        qid = b.get("battle",{}).get("value","").split("/")[-1]
        if qid in seen: continue
        seen.add(qid)
        try:
            lon = float(b["lon"]["value"])
            lat = float(b["lat"]["value"])
        except (KeyError, ValueError):
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "id":       qid,
                "name":     b.get("battleLabel",{}).get("value",""),
                "date":     (b.get("date",{}).get("value","") or "")[:10],
                "outcome":  b.get("outcomeLabel",{}).get("value",""),
                "war":      "Anglo-Sikh War",
                "type":     "battle",
                "source":   "Wikidata",
            },
        })
    return {"type": "FeatureCollection", "features": features}

def fetch_misl_capitals():
    """12 Sikh Misls — capitals with coordinates."""
    # Hardcoded since Wikidata coverage is sparse for Misls
    misls = [
        {"name": "Bhangi Misl",   "capital": "Gujranwala", "lon": 74.192, "lat": 32.162, "territory": "central Punjab"},
        {"name": "Sukerchakia",   "capital": "Gujranwala", "lon": 74.192, "lat": 32.162, "territory": "NW Punjab (Ranjit Singh)"},
        {"name": "Ahluwalia",     "capital": "Kapurthala",  "lon": 75.380, "lat": 31.381, "territory": "Doaba"},
        {"name": "Ramgarhia",     "capital": "Sri Hargobindpur","lon": 75.379, "lat": 31.828, "territory": "central Doaba"},
        {"name": "Kanhaiya",      "capital": "Sohian",      "lon": 74.800, "lat": 31.900, "territory": "Gurdaspur area"},
        {"name": "Nakkai",        "capital": "Chunian",     "lon": 74.000, "lat": 30.929, "territory": "south Punjab"},
        {"name": "Phulkian",      "capital": "Patiala",     "lon": 76.381, "lat": 30.340, "territory": "Malwa"},
        {"name": "Shahid Misl",   "capital": "Amritsar",    "lon": 74.879, "lat": 31.634, "territory": "Majha (guardians of Darbar Sahib)"},
        {"name": "Nishanwalia",   "capital": "Ambala",      "lon": 76.782, "lat": 30.378, "territory": "SE Malwa"},
        {"name": "Dallewalia",    "capital": "Fatehpur Kherian","lon": 75.238, "lat": 31.658, "territory": "Doaba"},
        {"name": "Karora Singhia","capital": "Batala",      "lon": 75.203, "lat": 31.818, "territory": "Majha"},
        {"name": "Faizullapuria", "capital": "Fatehabad",   "lon": 75.460, "lat": 29.517, "territory": "south Haryana"},
    ]
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [m["lon"], m["lat"]]},
            "properties": {
                "id":       "misl-" + m["name"].split()[0].lower(),
                "name":     m["name"],
                "capital":  m["capital"],
                "territory":m["territory"],
                "type":     "misl_capital",
                "date":     "1748-1799",
                "source":   "curated",
            },
        }
        for m in misls
    ]
    return {"type": "FeatureCollection", "features": features}

def sikh_heritage_sites():
    """Key Sikh historical sites — curated with verified coordinates."""
    sites = [
        {"name":"Nankana Sahib (Parkash Asthan)", "lon":73.704,"lat":31.451,"type":"gurdwara","date":"1469","notes":"Birthplace of Guru Nanak Dev Ji"},
        {"name":"Harmandir Sahib (Golden Temple)","lon":74.876,"lat":31.620,"type":"gurdwara","date":"1604","notes":"Compiled Guru Granth Sahib, built by Guru Arjan Dev Ji"},
        {"name":"Anandpur Sahib",                  "lon":76.497,"lat":31.232,"type":"gurdwara","date":"1665","notes":"Founded by Guru Tegh Bahadur Ji; Khalsa founded 1699"},
        {"name":"Fatehgarh Sahib (Sirhind)",        "lon":76.387,"lat":30.641,"type":"gurdwara","date":"1705","notes":"Sahibzadey Shaheedi — two younger Sahibzade"},
        {"name":"Chamkaur Sahib",                   "lon":76.415,"lat":30.891,"type":"gurdwara","date":"1704","notes":"Battle of Chamkaur — two elder Sahibzade"},
        {"name":"Hazur Sahib, Nanded",              "lon":77.326,"lat":19.065,"type":"gurdwara","date":"1708","notes":"Guru Gobind Singh Ji Jyoti Jot"},
        {"name":"Muktsar Sahib",                    "lon":74.515,"lat":30.473,"type":"gurdwara","date":"1705","notes":"Muktsar battle — Chali Mukte"},
        {"name":"Jallianwala Bagh",                 "lon":74.879,"lat":31.620,"type":"memorial","date":"1919","notes":"Massacre by British forces, April 13 1919"},
        {"name":"Battle of Mudki",                  "lon":74.601,"lat":30.775,"type":"battle","date":"1845-12-18","notes":"First Anglo-Sikh War — first engagement"},
        {"name":"Battle of Sobraon",                "lon":74.430,"lat":31.070,"type":"battle","date":"1846-02-10","notes":"First Anglo-Sikh War — decisive British victory"},
        {"name":"Battle of Chillianwala",           "lon":73.530,"lat":32.720,"type":"battle","date":"1849-01-13","notes":"Second Anglo-Sikh War — Sikh tactical victory"},
        {"name":"Lahore Fort (Sikh Empire HQ)",     "lon":74.313,"lat":31.588,"type":"palace","date":"1799-1849","notes":"Capital of Sikh Empire under Maharaja Ranjit Singh"},
        {"name":"Chhota Ghalughara 1746",           "lon":75.400,"lat":32.000,"type":"battle","date":"1746","notes":"Mughal-Sikh confrontation, thousands killed"},
        {"name":"Vadda Ghalughara 1762",            "lon":75.890,"lat":30.530,"type":"battle","date":"1762","notes":"Ahmad Shah Durrani vs Sikh Khalsa — 20,000+ killed"},
    ]
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
            "properties": {**{k: v for k,v in s.items() if k not in ("lon","lat")}, "source": "curated"},
        }
        for s in sites
    ]
    return {"type": "FeatureCollection", "features": features}

def main():
    print("FALCON · fetch_history.py")
    now = datetime.datetime.utcnow()

    # Anglo-Sikh Wars from Wikidata
    battles_geo = {"type": "FeatureCollection", "features": []}
    try:
        battles_geo = fetch_anglo_sikh_wars()
    except Exception as e:
        print(f"[warn] Anglo-Sikh Wars query failed: {e}")

    # Merge with curated sites
    heritage = sikh_heritage_sites()
    battles_geo["features"].extend(heritage["features"])

    path_battles = HIST_DIR / "anglo_sikh_wars.geojson"
    path_battles.write_text(json.dumps(battles_geo, indent=2), encoding="utf-8")
    print(f"Written: {path_battles}  ({len(battles_geo['features'])} features)")

    # Misl capitals
    misl_geo = fetch_misl_capitals()
    path_misls = HIST_DIR / "misl_capitals.geojson"
    path_misls.write_text(json.dumps(misl_geo, indent=2), encoding="utf-8")
    print(f"Written: {path_misls}  ({len(misl_geo['features'])} features)")

    print(f"\nHistory layer complete at {now.strftime('%Y-%m-%d')}")

if __name__ == "__main__":
    main()
