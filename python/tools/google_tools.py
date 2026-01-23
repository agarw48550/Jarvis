#!/usr/bin/env python3
"""
Google Cloud API Tools for Jarvis.
Covers: Drive, Classroom, People, Directions, Places, Time Zone.
"""

import os
import time
from typing import Optional
import requests
from googleapiclient.discovery import build
from google_auth import get_credentials
from google.auth.transport.requests import Request

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")


def _get_service(name: str, version: str):
    """Get an authenticated Google API service."""
    creds = get_credentials()
    if not creds:
        return None
    return build(name, version, credentials=creds)


def _require_maps_key() -> Optional[str]:
    """Check if Google Maps API key is set."""
    if not GOOGLE_MAPS_API_KEY:
        return "Set GOOGLE_MAPS_API_KEY in your .env to use this feature."
    return None


# ============== Google Drive ==============

def list_drive_files(query: str = None, max_results: int = 10) -> str:
    """List files from Google Drive."""
    try:
        service = _get_service('drive', 'v3')
        if not service:
            return "Google Drive not set up. Run: python google_auth.py"
        
        params = {
            'pageSize': max_results,
            'fields': 'files(id, name, mimeType, modifiedTime)',
            'orderBy': 'modifiedTime desc',
        }
        if query:
            params['q'] = f"name contains '{query}'"
        
        results = service.files().list(**params).execute()
        files = results.get('files', [])
        
        if not files:
            return "No files found in Drive."
        
        summaries = []
        for f in files:
            name = f.get('name', 'Untitled')[:40]
            mime = f.get('mimeType', '').split('.')[-1][:15]
            summaries.append(f"{name} ({mime})")
        
        return f"Drive files: {', '.join(summaries)}"
        
    except Exception as e:
        return f"Drive error: {str(e)[:100]}"


def search_drive(query: str) -> str:
    """Search Google Drive for files matching a query."""
    if not query:
        return "Please provide a search query."
    return list_drive_files(query=query, max_results=5)


# ============== Google Classroom ==============

def list_classroom_courses() -> str:
    """List enrolled Google Classroom courses."""
    try:
        service = _get_service('classroom', 'v1')
        if not service:
            return "Google Classroom not set up. Run: python google_auth.py"
        
        results = service.courses().list(pageSize=10).execute()
        courses = results.get('courses', [])
        
        if not courses:
            return "No courses found."
        
        summaries = []
        for c in courses:
            name = c.get('name', 'Untitled')[:30]
            state = c.get('courseState', 'UNKNOWN')
            summaries.append(f"{name} ({state})")
        
        return f"Courses: {', '.join(summaries)}"
        
    except Exception as e:
        return f"Classroom error: {str(e)[:100]}"


def get_classroom_assignments(course_id: str = None, course_name: str = None) -> str:
    """Get coursework (assignments) from a Google Classroom course."""
    try:
        service = _get_service('classroom', 'v1')
        if not service:
            return "Google Classroom not set up. Run: python google_auth.py"
        
        # If course_name provided, find the course ID
        target_id = course_id
        if not target_id and course_name:
            courses = service.courses().list(pageSize=20).execute().get('courses', [])
            for c in courses:
                if course_name.lower() in c.get('name', '').lower():
                    target_id = c.get('id')
                    break
        
        if not target_id:
            return "Please provide a course ID or name."
        
        results = service.courses().courseWork().list(
            courseId=target_id, pageSize=10, orderBy='dueDate desc'
        ).execute()
        work = results.get('courseWork', [])
        
        if not work:
            return "No assignments found for this course."
        
        summaries = []
        for w in work:
            title = w.get('title', 'Untitled')[:30]
            due = w.get('dueDate')
            due_str = f"{due.get('month')}/{due.get('day')}" if due else "no due date"
            summaries.append(f"{title} (due {due_str})")
        
        return f"Assignments: {', '.join(summaries)}"
        
    except Exception as e:
        return f"Classroom error: {str(e)[:100]}"


# ============== Google People (Contacts) ==============

def get_contacts(query: str = None, max_results: int = 10) -> str:
    """Search contacts using Google People API."""
    try:
        service = _get_service('people', 'v1')
        if not service:
            return "Google Contacts not set up. Run: python google_auth.py"
        
        if query:
            # Use searchContacts for queries
            results = service.people().searchContacts(
                query=query,
                readMask='names,emailAddresses,phoneNumbers',
                pageSize=max_results
            ).execute()
            people = results.get('results', [])
            contacts = [p.get('person', {}) for p in people]
        else:
            # List connections
            results = service.people().connections().list(
                resourceName='people/me',
                personFields='names,emailAddresses,phoneNumbers',
                pageSize=max_results
            ).execute()
            contacts = results.get('connections', [])
        
        if not contacts:
            return "No contacts found."
        
        summaries = []
        for c in contacts:
            names = c.get('names', [])
            name = names[0].get('displayName', 'Unknown') if names else 'Unknown'
            emails = c.get('emailAddresses', [])
            email = emails[0].get('value', '') if emails else ''
            if email:
                summaries.append(f"{name} <{email}>")
            else:
                summaries.append(name)
        
        return f"Contacts: {', '.join(summaries)}"
        
    except Exception as e:
        return f"Contacts error: {str(e)[:100]}"


# ============== Google Maps Directions ==============

def get_directions(origin: str, destination: str, mode: str = "driving") -> str:
    """Get directions between two locations using Google Directions API."""
    err = _require_maps_key()
    if err:
        return err
    
    if not origin or not destination:
        return "Please provide origin and destination."
    
    try:
        url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            "origin": origin,
            "destination": destination,
            "mode": mode.lower(),
            "key": GOOGLE_MAPS_API_KEY,
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "OK":
            return f"Directions error: {data.get('status')}"
        
        route = data.get("routes", [{}])[0]
        leg = route.get("legs", [{}])[0]
        
        distance = leg.get("distance", {}).get("text", "unknown")
        duration = leg.get("duration", {}).get("text", "unknown")
        
        steps = leg.get("steps", [])[:3]
        instructions = []
        for s in steps:
            instr = s.get("html_instructions", "").replace("<b>", "").replace("</b>", "")
            instr = instr.replace("<div style=\"font-size:0.9em\">", " ").replace("</div>", "")
            if instr:
                instructions.append(instr[:50])
        
        summary = f"From {origin} to {destination} ({mode}): {distance}, {duration}."
        if instructions:
            summary += f" First steps: {'; '.join(instructions)}"
        
        return summary
        
    except Exception as e:
        return f"Directions error: {str(e)[:100]}"


# ============== Google Places ==============

def get_places_nearby(location: str = None, place_type: str = "restaurant", radius: int = 1000, lat: float = None, lon: float = None) -> str:
    """Find nearby places using Google Places API."""
    err = _require_maps_key()
    if err:
        return err
    
    try:
        # If location string provided, geocode it first
        if location and not (lat and lon):
            geo_url = "https://maps.googleapis.com/maps/api/geocode/json"
            geo_resp = requests.get(geo_url, params={"address": location, "key": GOOGLE_MAPS_API_KEY}, timeout=10)
            geo_data = geo_resp.json()
            if geo_data.get("status") == "OK":
                loc = geo_data["results"][0]["geometry"]["location"]
                lat, lon = loc["lat"], loc["lng"]
            else:
                return f"Could not geocode location: {location}"
        
        if not (lat and lon):
            return "Please provide a location or coordinates."
        
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            "location": f"{lat},{lon}",
            "radius": radius,
            "type": place_type,
            "key": GOOGLE_MAPS_API_KEY,
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") not in ["OK", "ZERO_RESULTS"]:
            return f"Places error: {data.get('status')}"
        
        places = data.get("results", [])[:5]
        if not places:
            return f"No {place_type}s found near {location or 'that location'}."
        
        summaries = []
        for p in places:
            name = p.get("name", "Unknown")[:25]
            rating = p.get("rating", "N/A")
            summaries.append(f"{name} ({rating}★)")
        
        return f"Nearby {place_type}s: {', '.join(summaries)}"
        
    except Exception as e:
        return f"Places error: {str(e)[:100]}"


# ============== Google Time Zone ==============

def get_timezone(lat: float = None, lon: float = None, location: str = None) -> str:
    """Get timezone information for coordinates or a location."""
    err = _require_maps_key()
    if err:
        return err
    
    try:
        # If location string provided, geocode it first
        if location and not (lat and lon):
            geo_url = "https://maps.googleapis.com/maps/api/geocode/json"
            geo_resp = requests.get(geo_url, params={"address": location, "key": GOOGLE_MAPS_API_KEY}, timeout=10)
            geo_data = geo_resp.json()
            if geo_data.get("status") == "OK":
                loc = geo_data["results"][0]["geometry"]["location"]
                lat, lon = loc["lat"], loc["lng"]
            else:
                return f"Could not geocode location: {location}"
        
        if lat is None or lon is None:
            return "Please provide coordinates (lat, lon) or a location name."
        
        url = "https://maps.googleapis.com/maps/api/timezone/json"
        params = {
            "location": f"{lat},{lon}",
            "timestamp": int(time.time()),
            "key": GOOGLE_MAPS_API_KEY,
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "OK":
            return f"Timezone error: {data.get('status')}"
        
        tz_id = data.get("timeZoneId", "Unknown")
        tz_name = data.get("timeZoneName", "Unknown")
        offset_sec = data.get("rawOffset", 0) + data.get("dstOffset", 0)
        offset_hrs = offset_sec / 3600
        
        loc_str = location or f"({lat}, {lon})"
        return f"Timezone for {loc_str}: {tz_name} ({tz_id}), UTC{offset_hrs:+.1f}"
        
    except Exception as e:
        return f"Timezone error: {str(e)[:100]}"
