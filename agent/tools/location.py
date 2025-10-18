import requests
from typing import Tuple

def where_am_i() -> Tuple[str, str, str]:
    """Approximate city/region/country via IP geolocation."""
    try:
        resp = requests.get("https://ipapi.co/json/", timeout=8)
        resp.raise_for_status()
        data = resp.json()
        city = data.get("city") or ""
        region = data.get("region") or ""
        country = data.get("country_name") or ""
        return city, region, country
    except Exception:
        return "", "", ""
