"""
Agent 9 - Volunteer Coordination Agent

Purpose: match nearest skilled volunteers (medical / engineer / driver) to
outstanding tasks implied by the current disaster response.
"""
from typing import List
from backend.models.schemas import PriorityItem, VolunteerAssignment
from backend.utils import haversine_km

TASK_SKILL_MAP = {
    "hospital": "medical",
    "school": "medical",
    "residential": "engineer",
    "warehouse": "driver",
}


def assign_volunteers(priorities: List[PriorityItem], volunteers: list, top_n: int = 3) -> List[VolunteerAssignment]:
    assignments = []
    for target in priorities[:top_n]:
        needed_skill = TASK_SKILL_MAP.get(target.entity_type, "medical")
        pool = [v for v in volunteers if v["available"] and v["skill"] == needed_skill]
        if not pool:
            pool = [v for v in volunteers if v["available"]]
        if not pool:
            continue
        nearest = min(pool, key=lambda v: haversine_km(v["lat"], v["lon"], target.lat, target.lon))
        dist = haversine_km(nearest["lat"], nearest["lon"], target.lat, target.lon)
        nearest["available"] = False

        assignments.append(
            VolunteerAssignment(
                volunteer_name=nearest["name"],
                skill=nearest["skill"],
                assigned_task=f"Support response at {target.entity}",
                distance_km=round(dist, 2),
            )
        )
    return assignments
