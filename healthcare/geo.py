"""Calculs de distance (sphère) pour le filtrage « à proximité » — compatible OSM / GPS."""
from __future__ import annotations

import math
from typing import Optional, Tuple


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance en kilomètres entre deux points WGS84."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def parse_lat_lng(lat_s: Optional[str], lng_s: Optional[str]) -> Optional[Tuple[float, float]]:
    if lat_s is None or lng_s is None or lat_s == "" or lng_s == "":
        return None
    try:
        lat = float(lat_s)
        lng = float(lng_s)
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None
    return lat, lng


def parse_radius_km(val: Optional[str], default: float = 30.0) -> float:
    if val is None or val == "":
        return default
    try:
        r = float(val)
    except (TypeError, ValueError):
        return default
    return max(1.0, min(r, 200.0))
