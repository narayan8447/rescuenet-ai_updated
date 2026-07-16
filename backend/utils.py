"""
Shared utility functions used across multiple agents.
"""
import math
import random


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometres."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def jitter_point(lat: float, lon: float, max_km: float = 5.0):
    """Return a random point within max_km of (lat, lon). Used to simulate
    multiple affected sub-areas / facilities around a disaster's epicentre."""
    d = random.uniform(0.2, max_km)
    bearing = random.uniform(0, 2 * math.pi)
    r = 6371.0
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    lat2 = math.asin(math.sin(lat1) * math.cos(d / r) + math.cos(lat1) * math.sin(d / r) * math.cos(bearing))
    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(d / r) * math.cos(lat1),
        math.cos(d / r) - math.sin(lat1) * math.sin(lat2),
    )
    return round(math.degrees(lat2), 5), round(math.degrees(lon2), 5)


def seeded_random(seed_text: str) -> random.Random:
    """Deterministic RNG per disaster event so re-running the same input
    location/type produces a consistent, explainable simulation."""
    rng = random.Random()
    rng.seed(seed_text)
    return rng
