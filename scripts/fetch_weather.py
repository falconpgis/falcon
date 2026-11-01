"""
FALCON — Engine IV: Open-Meteo weather + rainfall fetcher
Free API, no key required. Daily rainfall for Punjab bbox.
Outputs:
  public/data/weather.json        — current + 7-day forecast
  public/data/history/weather_timeseries.json — daily rainfall history
"""
import json, datetime, requests
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "public" / "data"
HIST_DIR = DATA_DIR / "history"
HIST_DIR.mkdir(parents=True, exist_ok=True)

# Punjab centroid (India) — representative station
LAT, LON = 30.9, 75.8  # near Ludhiana

BASE = "https://api.open-meteo.com/v1/forecast"

def fetch_forecast():
    params = {
        "latitude": LAT,
        "longitude": LON,
        "daily": [
            "precipitation_sum",
            "precipitation_probability_max",
            "temperature_2m_max",
            "temperature_2m_min",
            "windspeed_10m_max",
        ],
        "hourly": ["relative_humidity_2m"],
        "current_weather": True,
        "timezone": "Asia/Kolkata",
        "forecast_days": 10,
    }
    r = requests.get(BASE, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def compute_signals(daily):
    """Drought / flood signals from 10-day forecast."""
    rain_7d = sum((daily.get("precipitation_sum") or [])[:7])
    normal_7d = 7 * 2.5  # 2.5 mm/day avg (kharif season rough normal)
    anomaly_pct = ((rain_7d - normal_7d) / max(normal_7d, 0.1)) * 100

    if rain_7d < 2:
        drought_signal = "CRITICAL"
    elif rain_7d < 10:
        drought_signal = "DRY"
    elif rain_7d > 80:
        drought_signal = "FLOOD_RISK"
    else:
        drought_signal = "NORMAL"

    return {
        "rain_7d_mm":      round(rain_7d, 1),
        "anomaly_pct":     round(anomaly_pct, 1),
        "drought_signal":  drought_signal,
    }

def main():
    print("FALCON · fetch_weather.py")
    now = datetime.datetime.utcnow()

    try:
        raw = fetch_forecast()
    except Exception as e:
        print(f"[error] {e}")
        return

    daily  = raw.get("daily", {})
    dates  = daily.get("time", [])
    rain   = daily.get("precipitation_sum", [])
    prob   = daily.get("precipitation_probability_max", [])
    tmax   = daily.get("temperature_2m_max", [])
    tmin   = daily.get("temperature_2m_min", [])
    wind   = daily.get("windspeed_10m_max", [])
    cur    = raw.get("current_weather", {})

    forecast_days = [
        {
            "date":       dates[i],
            "rain_mm":    rain[i] if i < len(rain) else None,
            "rain_prob":  prob[i] if i < len(prob) else None,
            "temp_max":   tmax[i] if i < len(tmax) else None,
            "temp_min":   tmin[i] if i < len(tmin) else None,
            "wind_kmh":   wind[i] if i < len(wind) else None,
        }
        for i in range(len(dates))
    ]

    signals = compute_signals(daily)

    output = {
        "fetched_utc":   now.isoformat() + "Z",
        "station":       {"lat": LAT, "lon": LON, "name": "Ludhiana (Punjab centroid)"},
        "current":       cur,
        "forecast":      forecast_days,
        "signals":       signals,
    }

    out_path = DATA_DIR / "weather.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Written: {out_path}")
    print(f"  Rain 7d: {signals['rain_7d_mm']} mm  Signal: {signals['drought_signal']}")

    # Timeseries history
    hist_path = HIST_DIR / "weather_timeseries.json"
    history = []
    if hist_path.exists():
        try:
            history = json.loads(hist_path.read_text(encoding="utf-8"))
        except Exception:
            history = []

    # Add today's entry
    today = forecast_days[0] if forecast_days else {}
    history.append({
        "snapshot_date": now.strftime("%Y-%m-%d"),
        "rain_mm":       today.get("rain_mm"),
        "temp_max":      today.get("temp_max"),
        "temp_min":      today.get("temp_min"),
        "drought_signal":signals["drought_signal"],
        "rain_7d_mm":    signals["rain_7d_mm"],
        "anomaly_pct":   signals["anomaly_pct"],
    })
    history = history[-365:]  # 1 year rolling
    hist_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    print(f"History: {hist_path} ({len(history)} entries)")

if __name__ == "__main__":
    main()
