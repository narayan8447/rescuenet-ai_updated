"""
Agent 4 - Resource Allocation Agent

Purpose: an optimization engine that assigns available ambulances, fire
trucks, boats, and helicopters to the highest-priority locations, nearest
resource first. Mutates the shared in-memory `resources` state so a resource
that's dispatched becomes unavailable for the rest of the run (mirrors a
live Redis availability feed).
"""
from typing import List
from backend.models.schemas import PriorityItem, ResourceAssignment
from backend.utils import haversine_km

DISASTER_RESOURCE_NEEDS = {
    "flood": ["boat", "ambulance"],
    "earthquake": ["fire_truck", "ambulance", "helicopter"],
    "cyclone": ["fire_truck", "boat", "ambulance"],
    "fire": ["fire_truck", "ambulance"],
    "landslide": ["fire_truck", "helicopter", "ambulance"],
    "building_collapse": ["fire_truck", "ambulance", "helicopter"],
}

AVG_SPEED_KMH = {"boat": 25, "ambulance": 40, "fire_truck": 35, "helicopter": 180}


def allocate(disaster_type: str, priorities: List[PriorityItem], resources: dict, top_n: int = 4) -> List[ResourceAssignment]:
    needed_types = DISASTER_RESOURCE_NEEDS.get(disaster_type, ["ambulance"])
    assignments = []

    targets = priorities[:top_n]
    for target in targets:
        for rtype in needed_types:
            pool = [r for r in resources.get(rtype, []) if r["available"]]
            if not pool:
                continue
            nearest = min(pool, key=lambda r: haversine_km(r["lat"], r["lon"], target.lat, target.lon))
            dist = haversine_km(nearest["lat"], nearest["lon"], target.lat, target.lon)
            speed = AVG_SPEED_KMH.get(rtype, 30)
            eta = round((dist / speed) * 60, 1)

            nearest["available"] = False  # dispatch: remove from pool
            assignments.append(
                ResourceAssignment(
                    resource_type=rtype,
                    resource_id=nearest["id"],
                    assigned_to=target.entity,
                    distance_km=round(dist, 2),
                    eta_minutes=eta,
                )
            )
    return assignments
