# FALCON — Punjab Geospatial Intelligence System

**Making the invisible visible — from space, across time, for everyone.**

A free public intelligence platform for Punjab: environment, agriculture, economy, history, geopolitics, and civilisational record — all in one 3D globe.

🌐 **Live**: [falconpgis.github.io/falcon](https://falconpgis.github.io/falcon)

---

## Five Engines

| # | Engine | What it shows |
|---|--------|---------------|
| **I** | History | Sikh historical sites, Ghalughara, Anglo-Sikh Wars, Partition 1947 |
| **II** | Live | NASA fire hotspots · CPCB AQI · AGMARKNET mandi prices · CGWB groundwater |
| **III** | Geo | Border incidents · CPEC · INSTC corridor · SYL water dispute · nuclear sites |
| **IV** | Future | Doaba Distress Index — composite 0-10 score by district |
| **V** | Diaspora | Sikh population worldwide · diaspora currencies vs INR |

---

## Data Sources

| Layer | Source | Pipeline |
|-------|--------|----------|
| Fire hotspots | NASA FIRMS VIIRS NRT | Daily (GitHub Actions) |
| Air quality | CPCB Open Data | Daily |
| Mandi prices | AGMARKNET / data.gov.in | Daily |
| Groundwater | CGWB 2023-24 | Static (quarterly refresh) |
| Currencies | ExchangeRate-API | Daily |
| Commodities | World Bank Pink Sheet | Monthly |
| Sikh sites | SGPC / Gurdwara records | Static |

---

## Tech Stack

- **CesiumJS 1.120** — 3D globe (CDN, no build tools)
- **GitHub Actions** — daily/monthly data pipeline
- **GitHub Pages** — free static hosting
- **No server. No database. No API key exposed.**

---

## GitHub Secrets Required

| Secret | Used by |
|--------|---------|
| `FIRMS_MAP_KEY` | `scripts/fetch_firms.py` — NASA FIRMS API |

---

## Run Locally

```bash
# Any static file server works — Python example:
python -m http.server 8080
# Then open http://localhost:8080
```

No build step. No npm. Open `index.html` directly or serve from project root.

---

## Project Structure

```
falcon/
├── index.html                    # Single-page app
├── src/
│   ├── main.js                   # Engine switching, startup
│   └── layers/
│       ├── fires.js              # Engine II — NASA FIRMS
│       ├── groundwater.js        # Engine II — CGWB
│       ├── aqi.js                # Engine II — CPCB AQI
│       ├── mandi.js              # Engine II — AGMARKNET
│       ├── history.js            # Engine I  — Sikh sites
│       ├── geopolitical.js       # Engine III — borders/CPEC
│       ├── prediction.js         # Engine IV — DDI scores
│       └── diaspora.js           # Engine V  — global Sikhs
├── scripts/
│   ├── fetch_firms.py
│   ├── fetch_aqi.py
│   ├── fetch_mandi.py
│   ├── fetch_currencies.py
│   └── fetch_commodities.py
├── public/data/
│   ├── punjab_fires.geojson
│   ├── punjab_aqi.json
│   ├── punjab_mandi.json
│   ├── punjab_groundwater.geojson
│   ├── currencies.json
│   ├── commodities.json
│   └── history/                  # Timeseries accumulation
│       ├── fires_timeseries.json
│       ├── aqi_timeseries.json
│       ├── mandi_timeseries.json
│       └── commodities_timeseries.json
└── .github/workflows/
    ├── daily.yml    # 00:30 UTC — fires, AQI, mandi, currencies
    └── monthly.yml  # 1st of month — commodities
```

---

## Civilisational Purpose

Punjab has been the world's most invaded corridor for 5,000 years. FALCON exists to give every Punjabi — farmer, diaspora, researcher, activist — the same intelligence picture that only governments and corporations had before.

Free. Open. Permanent record.

---

*Built with CesiumJS · NASA · CPCB · CGWB · AGMARKNET · World Bank*
