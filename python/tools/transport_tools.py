#!/usr/bin/env python3
"""
Singapore transport tools powered by LTA DataMall + OpenStreetMap.
"""

import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

import requests

from core.memory import get_preferences, set_preference

LTA_API_KEY = os.getenv("LTA_API_KEY", "")
LTA_BASE_URL = "https://datamall2.mytransport.sg/ltaodataservice"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
BUS_STOP_CACHE = DATA_DIR / "bus_stops.json"
BUS_STOP_CACHE_TTL = 60 * 60 * 24 * 7  # 1 week

USER_AGENT = "JarvisAssistant/1.0 (+https://github.com/ayaanagarwal/Jarvis)"


# ============== Helpers ==============

def _require_lta_key() -> Optional[str]:
    if not LTA_API_KEY:
        return "Set LTA_API_KEY in your .env to use Datamall."
    return None


def _nominatim_geocode(query: str) -> Optional[dict]:
    try:
        response = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if not data:
            return None
        return data[0]
    except Exception:
        return None


def _ensure_bus_stop_cache(force_refresh: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Download BusStops dataset if missing/expired.
    Returns (ok, message)
    """
    if not force_refresh and BUS_STOP_CACHE.exists():
        age = time.time() - BUS_STOP_CACHE.stat().st_mtime
        if age < BUS_STOP_CACHE_TTL:
            return True, None

    missing_key = _require_lta_key()
    if missing_key:
        return False, missing_key

    try:
        stops: List[dict] = []
        skip = 0
        while True:
            response = requests.get(
                f"{LTA_BASE_URL}/BusStops",
                headers={
                    "AccountKey": LTA_API_KEY,
                    "accept": "application/json",
                },
                params={"$skip": skip},
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
            batch = payload.get("value", [])
            if not batch:
                break
            stops.extend(batch)
            if len(batch) < 500:
                break
            skip += 500
        BUS_STOP_CACHE.write_text(json.dumps(stops, indent=2))
        return True, None
    except Exception as exc:
        return False, f"Couldn't refresh bus stops: {exc}"


def _load_bus_stops() -> List[dict]:
    if not BUS_STOP_CACHE.exists():
        ok, msg = _ensure_bus_stop_cache()
        if not ok:
            raise RuntimeError(msg or "Bus stop data unavailable.")
    try:
        return json.loads(BUS_STOP_CACHE.read_text())
    except Exception as exc:
        raise RuntimeError(f"Bus stop cache corrupt: {exc}") from exc


def _get_home_location() -> Tuple[Optional[float], Optional[float], Optional[str]]:
    prefs = get_preferences()
    lat = prefs.get("home_lat")
    lon = prefs.get("home_lon")
    label = prefs.get("home_location_label")
    if lat and lon:
        try:
            return float(lat), float(lon), label
        except ValueError:
            return None, None, None
    return None, None, None


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in meters."""
    r = 6371000  # Earth radius
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def _fetch_bus_arrivals(stop_code: str, service_no: Optional[str] = None) -> dict:
    missing_key = _require_lta_key()
    if missing_key:
        raise RuntimeError(missing_key)

    params = {"BusStopCode": stop_code}
    if service_no:
        params["ServiceNo"] = service_no

    response = requests.get(
        f"{LTA_BASE_URL}/BusArrivalv2",
        headers={
            "AccountKey": LTA_API_KEY,
            "accept": "application/json",
        },
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def _minutes_until(iso_timestamp: str) -> Optional[int]:
    if not iso_timestamp:
        return None
    try:
        arrival = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = arrival - now
        minutes = max(0, int(delta.total_seconds() // 60))
        return minutes
    except Exception:
        return None


def _format_service(service: dict) -> str:
    svc = service.get("ServiceNo", "Unknown")
    buses = [service.get("NextBus"), service.get("NextBus2"), service.get("NextBus3")]
    times = []
    for bus in buses:
        if not bus:
            continue
        mins = _minutes_until(bus.get("EstimatedArrival"))
        load = bus.get("Load")
        if mins is None:
            continue
        load_hint = ""
        if load == "SEA":
            load_hint = " (seats)"
        elif load == "SDA":
            load_hint = " (standing)"
        elif load == "LSD":
            load_hint = " (packed)"
        times.append(f"{mins}m{load_hint}")
    if not times:
        return f"Service {svc}: no live data."
    return f"Service {svc}: {', '.join(times)}."


def _summarize_bus_stop(stop_code: str, description: Optional[str], service_no: Optional[str] = None) -> str:
    try:
        payload = _fetch_bus_arrivals(stop_code, service_no)
    except Exception as exc:
        if "404" in str(exc):
            return "Couldn't reach Datamall (404 Not Found). Check API endpoint or key permissions."
        return f"Couldn't reach Datamall ({exc})"

    services = payload.get("Services", [])
    if not services:
        return f"No buses arriving soon at stop {stop_code}."

    desc = (description or payload.get("BusStopCode") or stop_code)
    lines = [f"{desc} (#{stop_code}):"]
    for svc in services:
        lines.append(_format_service(svc))
    return " ".join(lines)


# ============== Public API (tools) ==============

def set_home_location(query: str = None, location: str = None) -> str:
    """Save home location"""
    address = query or location
    if not address:
        return "Tell me an address or postal code."
    result = _nominatim_geocode(address)
    if not result:
        return "I couldn't find that location. Try a different description."
    lat = result.get("lat")
    lon = result.get("lon")
    if not lat or not lon:
        return "Location lookup returned incomplete data."
    label = result.get("display_name") or query or location or "Saved location"
    set_preference("home_lat", lat)
    set_preference("home_lon", lon)
    set_preference("home_location_label", label)
    return f"Location saved: {label.split(',')[0]}"


def get_home_location_label() -> str:
    lat, lon, label = _get_home_location()
    if lat is None or lon is None:
        return "No saved home location. Say 'set location <address>'."
    short = label.split(",")[0] if label else "saved location"
    return f"Saved location: {short} (lat {lat:.4f}, lon {lon:.4f})."


def sg_bus_arrival(stop_code: str, service_no: Optional[str] = None) -> str:
    stop_code = str(stop_code).strip()
    if not stop_code:
        return "Provide a BusStopCode, e.g., '12345'."
    return _summarize_bus_stop(stop_code, None, service_no)


def find_bus_stop(query: str) -> str:
    """Find bus stop codes by name/description"""
    query = query.lower().strip()
    if not query:
        return "Provide a location or bus stop name."
        
    try:
        stops = _load_bus_stops()
    except RuntimeError as exc:
        return str(exc)
        
    matches = []
    for stop in stops:
        desc = (stop.get("Description") or "").lower()
        road = (stop.get("RoadName") or "").lower()
        code = str(stop.get("BusStopCode") or "")
        
        if query in desc or query in road or query == code:
            matches.append(stop)
            
    if not matches:
        return f"No bus stops found matching '{query}'."
        
    # Sort by relevance (exact match first)
    matches.sort(key=lambda x: 0 if query == str(x.get("BusStopCode")) else 1)
    
    # Return top 5
    results = []
    for m in matches[:5]:
        code = m.get("BusStopCode")
        desc = m.get("Description")
        road = m.get("RoadName")
        results.append(f"{desc} ({code}) on {road}")
        
    return f"Found {len(matches)} stops. Top matches:\n" + "\n".join(results)


def refresh_bus_stops() -> str:
    ok, msg = _ensure_bus_stop_cache(force_refresh=True)
    if not ok:
        return msg or "Failed refreshing bus stops."
    return "Bus stop list refreshed."


def sg_bus_arrival_near_me(max_stops: int = 3, radius_m: int = 500) -> str:
    lat, lon, label = _get_home_location()
    if lat is None or lon is None:
        return "Set your location first (e.g., 'set location 039593')."

    try:
        stops = _load_bus_stops()
    except RuntimeError as exc:
        return str(exc)

    near = []
    for stop in stops:
        try:
            s_lat = float(stop.get("Latitude", 0))
            s_lon = float(stop.get("Longitude", 0))
        except (TypeError, ValueError):
            continue
        distance = _haversine(lat, lon, s_lat, s_lon)
        if distance <= radius_m:
            near.append((distance, stop))

    if not near:
        return f"No bus stops within {radius_m}m of your saved location."

    near.sort(key=lambda x: x[0])
    summaries = []
    for distance, stop in near[:max_stops]:
        desc = stop.get("Description") or stop.get("RoadName")
        stop_code = stop.get("BusStopCode")
        summary = _summarize_bus_stop(stop_code, desc)
        summaries.append(summary)

    header = f"Buses near {label.split(',')[0] if label else 'you'}:"
    return " ".join([header] + summaries)
