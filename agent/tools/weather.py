from typing import Dict, Any
import requests


def _geocode_city(city: str) -> tuple[float, float] | None:
    city = (city or "").strip()
    if not city:
        return None
    # Use Open-Meteo Geocoding (no key) https://geocoding-api.open-meteo.com
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=8,
        )
        r.raise_for_status()
        data = r.json()
        res = data.get("results") or []
        if not res:
            return None
        lat = float(res[0]["latitude"])  # type: ignore[index]
        lon = float(res[0]["longitude"])  # type: ignore[index]
        return lat, lon
    except Exception:
        return None


def weather_report(location: str) -> Dict[str, Any]:
    """Get a compact current weather report for a city using Open-Meteo.
    Returns keys: city, temperature_c, wind_kph, condition, humidity (if available).
    """
    city = (location or "").strip()
    latlon = _geocode_city(city)
    if not latlon:
        return {"error": f"Couldn't geolocate '{city}'."}
    lat, lon = latlon
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": True,
                "hourly": "relativehumidity_2m",
            },
            timeout=8,
        )
        r.raise_for_status()
        data = r.json()
        cw = data.get("current_weather", {})
        out: Dict[str, Any] = {
            "city": city,
            "temperature_c": cw.get("temperature"),
            "wind_kph": cw.get("windspeed"),
        }
        # Optional humidity from the first hourly point (approx)
        try:
            hum_series = (data.get("hourly", {}) or {}).get("relativehumidity_2m")
            if isinstance(hum_series, list) and hum_series:
                out["humidity"] = hum_series[0]
        except Exception:
            pass
        # Map weathercode to a simple condition (minimal mapping)
        code = cw.get("weathercode")
        cond = {
            0: "Clear",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
        }.get(code, None)
        if cond:
            out["condition"] = cond
        return out
    except Exception as e:
        return {"error": str(e)}
