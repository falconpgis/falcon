"""
FALCON — Engine II: CGWB groundwater level fetcher
Source: Central Ground Water Board — cgwb.gov.in (PDF scraping)
Tier 1: attempt PDF download + text extraction (pdfminer.six)
Tier 2: fallback to latest known quarterly bulletin values

Outputs:
  public/data/punjab_groundwater.geojson  — district-level depth readings
  public/data/history/groundwater_timeseries.json — quarterly snapshots
"""
import json, datetime, re, requests
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "public" / "data"
HIST_DIR = DATA_DIR / "history"
HIST_DIR.mkdir(parents=True, exist_ok=True)

# CGWB district wells — 22 Punjab districts with coordinates
DISTRICTS = {
    "Amritsar":      (74.879, 31.634),
    "Gurdaspur":     (75.406, 32.040),
    "Hoshiarpur":    (75.916, 31.532),
    "Jalandhar":     (75.577, 31.326),
    "Kapurthala":    (75.380, 31.381),
    "Ludhiana":      (75.857, 30.900),
    "Moga":          (75.172, 30.818),
    "SAS Nagar":     (76.704, 30.705),
    "Patiala":       (76.381, 30.340),
    "Rupnagar":      (76.531, 30.965),
    "SBS Nagar":     (76.082, 31.153),
    "Fatehgarh Sahib":(76.387,30.641),
    "Firozpur":      (74.613, 30.934),
    "Fazilka":       (74.024, 30.400),
    "Muktsar":       (74.515, 30.473),
    "Barnala":       (75.541, 30.378),
    "Sangrur":       (75.844, 30.245),
    "Bathinda":      (74.948, 30.210),
    "Mansa":         (75.391, 29.988),
    "Tarn Taran":    (74.928, 31.452),
    "Pathankot":     (75.652, 32.274),
    "Malerkotla":    (75.879, 30.532),
}

# Fallback data (2023 CGWB annual bulletin values, metres below ground level)
FALLBACK_MBL = {
    "Amritsar": 14.2, "Gurdaspur": 9.8,  "Hoshiarpur": 7.5,
    "Jalandhar": 16.4, "Kapurthala": 12.1,"Ludhiana": 22.3,
    "Moga": 25.1, "SAS Nagar": 18.7,     "Patiala": 13.6,
    "Rupnagar": 8.2, "SBS Nagar": 10.4,  "Fatehgarh Sahib": 15.8,
    "Firozpur": 6.8, "Fazilka": 5.9,     "Muktsar": 7.2,
    "Barnala": 28.4, "Sangrur": 31.2,    "Bathinda": 11.5,
    "Mansa": 9.3, "Tarn Taran": 19.6,    "Pathankot": 5.1,
    "Malerkotla": 26.7,
}

CGWB_BASE = "https://cgwb.gov.in"

def attempt_pdf_extract():
    """Try to download latest CGWB Punjab quarterly bulletin and extract values."""
    try:
        from pdfminer.high_level import extract_text
    except ImportError:
        print("[skip] pdfminer.six not installed, using fallback data")
        return None

    # Try known bulletin URLs (CGWB publishes quarterly PDFs)
    candidate_urls = [
        f"{CGWB_BASE}/Ground-Water/Groundwater-Data-Report/State-Report/Punjab/GW-Data-2023-Punjab.pdf",
        f"{CGWB_BASE}/Reports/Groundwater-Extraction/Punjab-GW-{datetime.datetime.now().year}.pdf",
    ]
    import tempfile, os
    for url in candidate_urls:
        try:
            r = requests.get(url, timeout=30, stream=True)
            if r.status_code != 200:
                continue
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                for chunk in r.iter_content(8192):
                    tmp.write(chunk)
                tmp_path = tmp.name
            text = extract_text(tmp_path)
            os.unlink(tmp_path)
            print(f"[PDF] extracted {len(text)} chars from {url}")
            return parse_cgwb_text(text)
        except Exception as e:
            print(f"[warn] PDF {url}: {e}")
    return None

def parse_cgwb_text(text):
    """
    Parse district depth values from CGWB bulletin text.
    Tables use format: District  <mbgl-value>
    Returns {district: depth_mbgl} or None if insufficient matches.
    """
    values = {}
    for district in DISTRICTS:
        # Match district name followed by a decimal number within ~200 chars
        pattern = re.compile(
            re.escape(district) + r'.*?(\d{1,2}\.\d{1})',
            re.IGNORECASE | re.DOTALL
        )
        m = pattern.search(text[:50000])
        if m:
            try:
                values[district] = float(m.group(1))
            except ValueError:
                pass
    print(f"[PDF] parsed {len(values)}/{len(DISTRICTS)} district values")
    return values if len(values) >= 10 else None

def build_geojson(depth_map, source):
    """Convert district depth readings to GeoJSON."""
    features = []
    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    for district, (lon, lat) in DISTRICTS.items():
        depth = depth_map.get(district, FALLBACK_MBL.get(district, 0))
        # Risk level
        if depth > 30:
            risk = "CRITICAL"
            color = "#d32f2f"
        elif depth > 20:
            risk = "HIGH"
            color = "#f57c00"
        elif depth > 12:
            risk = "MODERATE"
            color = "#fbc02d"
        else:
            risk = "LOW"
            color = "#388e3c"

        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "district":    district,
                "depth_mbgl":  round(depth, 1),
                "risk":        risk,
                "color":       color,
                "date":        now_str,
                "source":      source,
            },
        })
    return {"type": "FeatureCollection", "features": features}

def main():
    print("FALCON · fetch_groundwater.py")
    now = datetime.datetime.utcnow()

    # Try real PDF extraction first
    depth_map = attempt_pdf_extract()
    if depth_map:
        source = "CGWB-PDF"
        print(f"[source] PDF extraction succeeded")
    else:
        depth_map = dict(FALLBACK_MBL)
        source = "CGWB-2023-bulletin"
        print(f"[source] Using fallback 2023 bulletin values")

    geo = build_geojson(depth_map, source)
    geo_path = DATA_DIR / "punjab_groundwater.geojson"
    geo_path.write_text(json.dumps(geo, indent=2), encoding="utf-8")
    print(f"Written: {geo_path}  ({len(geo['features'])} districts)")

    # Timeseries snapshot
    hist_path = HIST_DIR / "groundwater_timeseries.json"
    history = []
    if hist_path.exists():
        try:
            history = json.loads(hist_path.read_text(encoding="utf-8"))
        except Exception:
            history = []

    avg_depth = sum(depth_map.values()) / len(depth_map) if depth_map else 0
    critical = sum(1 for v in depth_map.values() if v > 30)
    history.append({
        "snapshot_date":   now.strftime("%Y-%m-%d"),
        "avg_depth_mbgl":  round(avg_depth, 1),
        "critical_districts": critical,
        "source":          source,
        "districts":       {k: round(v, 1) for k, v in depth_map.items()},
    })
    history = history[-20:]  # 5 years of quarterly
    hist_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    print(f"History: {hist_path} ({len(history)} entries)")

    print(f"\nAvg depth: {avg_depth:.1f} mbgl  Critical districts: {critical}")
    worst = sorted(depth_map.items(), key=lambda x: -x[1])[:5]
    for d, v in worst:
        print(f"  {d:20s} {v:.1f} mbgl")

if __name__ == "__main__":
    main()
