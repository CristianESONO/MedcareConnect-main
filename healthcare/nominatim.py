"""Appels serveur vers l'API Nominatim (OpenStreetMap) — respecter la politique d'usage (User-Agent)."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
USER_AGENT = getattr(
    settings,
    "NOMINATIM_USER_AGENT",
    "MedCareConnect/1.0 (+https://medcareconnect.sn; contact@medcareconnect.sn)",
)


def _get_json(url: str, timeout: int = 10):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def search_places(query: str, limit: int = 5):
    if not query or len(query.strip()) < 2:
        return []
    params = urllib.parse.urlencode(
        {
            "q": query.strip(),
            "format": "json",
            "limit": str(min(max(limit, 1), 10)),
            "addressdetails": "1",
        }
    )
    url = f"{NOMINATIM_BASE}/search?{params}"
    try:
        data = _get_json(url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return []
    out = []
    for item in data:
        try:
            lat = float(item["lat"])
            lon = float(item["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        out.append(
            {
                "lat": lat,
                "lon": lon,
                "display_name": item.get("display_name", ""),
                "type": item.get("type", ""),
            }
        )
    return out


def reverse(lat: float, lon: float):
    params = urllib.parse.urlencode(
        {
            "lat": str(lat),
            "lon": str(lon),
            "format": "json",
            "addressdetails": "1",
        }
    )
    url = f"{NOMINATIM_BASE}/reverse?{params}"
    try:
        data = _get_json(url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None
    if not data or "lat" not in data:
        return None
    try:
        return {
            "lat": float(data["lat"]),
            "lon": float(data["lon"]),
            "display_name": data.get("display_name", ""),
        }
    except (KeyError, TypeError, ValueError):
        return None
