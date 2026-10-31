# FALCON — Punjab Geospatial Intelligence System (PGIS)

## Project Identity
- **Full name**: Punjab Geospatial Intelligence System
- **Codename**: FALCON
- **Tagline**: Making the invisible visible — from space, across time, for everyone
- **GitHub**: github.com/falconpgis/falcon
- **Live URL**: falconpgis.github.io/falcon
- **Purpose**: Free public intelligence platform for Punjab — environment, agriculture, economy, health, migration, history, geopolitics, civilisational record

## Tech Stack
- **Frontend**: CesiumJS (3D globe) + MapLibre GL JS (2D fallback for low-RAM devices)
- **Build**: Vite + vanilla JS
- **Hosting**: GitHub Pages (free)
- **Data pipeline**: GitHub Actions (free) → Python scripts → GeoJSON/JSON → public/data/
- **No server. No database. Static files only.**

## Five-Engine Architecture

### Engine 1 — Historical Record
What Punjab was: invasion corridor, Sikh Empire, colonisation, Partition
- Sikh historical GIS (Sri Nanak Parkash 4 Udasis, Sri Suraj Parkash 10 Guru Sahibans)
- 12 Misls with capitals and territories
- Anglo-Sikh Wars battle locations
- British Punjab canals and railways
- Partition 1947 — villages, displacement, massacres
- Backward satellite analysis: CORONA 1965 → Landsat 1972 → Sentinel-2 2026

### Engine 2 — Present Monitoring
What Punjab is now: fires, air, water, crops, economy
- NASA FIRMS fire detection (daily)
- CPCB air quality — AQI all Punjab stations (daily)
- AGMARKNET mandi prices — wheat, rice, cotton, vegetables (daily)
- CGWB groundwater levels (quarterly)
- Punjab government open data layers

### Engine 3 — Geopolitical Intelligence
What surrounds Punjab: borders, corridors, global signals
- India-Pakistan border — ACLED incidents
- CPEC route monitoring
- INSTC corridor
- Arctic shipping routes
- Global food security signals

### Engine 4 — Prediction & Foresight
What is coming: threshold alerts, composite indexes
- Doaba distress index (composite)
- Malwa farm input cost index
- Punjab fiscal crisis predictor
- Migration pressure index
- Early warning thresholds

### Engine 5 — Civilisational Intelligence
The Sikh people across the world
- Diaspora mapping (Canada, UK, Italy, Gulf, Australia)
- Financial signals (commodity prices, currencies, Baltic Dry Index)
- Gurdwara economy (SGPC budget, langar capacity)
- Population surveys

## File Structure
```
falcon/
├── CLAUDE.md                    ← this file
├── public/
│   └── data/
│       ├── punjab_fires.geojson         (daily — NASA FIRMS)
│       ├── punjab_aqi.json              (daily — CPCB)
│       ├── punjab_mandi.json            (daily — AGMARKNET)
│       ├── punjab_groundwater.geojson   (quarterly — CGWB)
│       ├── punjab_sdl_bonds.json        (weekly)
│       ├── currencies.json              (daily)
│       ├── commodities.json             (monthly)
│       ├── punjab_trends.json           (weekly — Google Trends)
│       ├── punjab_events.geojson        (weekly — ACLED)
│       └── punjab_historical/
│           ├── sikh_sites.geojson
│           ├── guru_udasis.geojson
│           ├── misl_territories.geojson
│           ├── anglo_sikh_wars.geojson
│           └── partition_1947.geojson
├── scripts/
│   ├── fetch_firms.py
│   ├── fetch_aqi.py
│   ├── fetch_mandi.py
│   ├── fetch_currencies.py
│   └── fetch_commodities.py
├── .github/workflows/
│   ├── daily.yml       (00:30 UTC — fires, AQI, mandi, currencies)
│   ├── weekly.yml      (Monday — trends, events, bonds)
│   └── monthly.yml     (1st — commodities, groundwater)
├── src/
│   ├── main.js
│   ├── layers/
│   └── ui/
└── index.html
```

## GitHub Secrets Required
- `FIRMS_MAP_KEY` — NASA FIRMS API key (already added)

## Data Sources
| Layer | Source | Frequency |
|-------|--------|-----------|
| Fire hotspots | NASA FIRMS VIIRS NRT | Daily |
| Air quality | CPCB (api.cpcbccr.com) | Daily |
| Mandi prices | AGMARKNET / data.gov.in | Daily |
| Groundwater | CGWB | Quarterly |
| Currencies | ExchangeRate-API (free tier) | Daily |
| Commodities | World Bank Pink Sheet | Monthly |
| Google Trends | pytrends | Weekly |
| Conflict events | ACLED API | Weekly |
| Bond yields | RBI / NSE | Weekly |

## Punjab Bounding Box
```
Lat: 29.5 — 32.5
Lon: 73.8 — 76.9
```
Use this to filter all data to Punjab only.

## Key Historical Coordinates
- Guru Nanak Dev Ji Parkash — Nankana Sahib: 31.451°N 73.704°E
- Guru Arjan Dev Ji Shaheedi — Lahore: 31.549°N 74.343°E
- Sahibzadey Shaheedi — Sirhind: 30.641°N 76.387°E
- Guru Gobind Singh Ji Jyoti Jot — Nanded: 19.065°N 77.326°E
- Chhota Ghalughara 1746: 32.0°N 75.4°E
- Vadda Ghalughara 1762: 30.53°N 75.89°E
- Jallianwala Bagh: 31.620°N 74.879°E
- Battle of Mudki: 30.775°N 74.601°E
- Battle of Sobraon: 31.07°N 74.43°E

## Code Rules
1. Always run runtime tests before presenting any file — static syntax check alone is not enough
2. Runtime test must call EVERY method referenced in the code
3. Present ONLY changed files — never full ZIP or full archive
4. No hardcoded API keys ever — use environment variables / GitHub Secrets
5. All data fetches must filter to Punjab bounding box
6. GeoJSON features must include `properties.date` and `properties.source`

## Build Priority Order
1. Phase 0 — Base globe loads, Punjab camera, FALCON branding
2. Phase 1 — NASA FIRMS fire layer (daily pipeline working)
3. Phase 2 — AQI layer + mandi prices layer
4. Phase 3 — Historical Sikh sites layer
5. Phase 4 — Groundwater + economic signals
6. Phase 5 — Prediction indexes + geopolitical layer

## Connected Project
**GURMAT TATGYAN** — separate project, Gurbani knowledge system
- Do not mix code between projects
- Shared geographic data (Gurdwara locations) will be pulled from PGIS historical layer
- Repo: github.com/falconpgis/falcon
