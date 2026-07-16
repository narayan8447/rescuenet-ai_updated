"""
Agent 3 - Rescue Prioritization Agent

Purpose: answer "who gets rescued first?" by scoring points of interest
(hospitals, schools, residential zones, warehouses) against nearby damage
severity, facility criticality, and population weight.
"""
from typing import List
from backend.models.schemas import DamageReport, PriorityItem
from backend.utils import haversine_km

TYPE_BASE_SCORE = {
    "hospital": 100,
    "school": 90,
    "residential": 70,
    "warehouse": 40,
}


def prioritize(damage_reports: List[DamageReport], points_of_interest: list) -> List[PriorityItem]:
    items = []
    for poi in points_of_interest:
        base = TYPE_BASE_SCORE.get(poi["type"], 50)

        # find nearest damage report to factor in local severity
        nearest = min(
            damage_reports,
            key=lambda d: haversine_km(poi["lat"], poi["lon"], d.lat, d.lon),
        )
        dist = haversine_km(poi["lat"], poi["lon"], nearest.lat, nearest.lon)
        proximity_factor = max(0.0, 1 - dist / 10)  # closer to worst-hit area -> higher weight

        score = base * 0.5 + nearest.severity_score * 0.35 * proximity_factor + poi["population_weight"] * 15
        score = round(min(score, 100.0), 1)

        reason = (
            f"{poi['type'].title()} near {nearest.area_id} "
            f"(severity {nearest.severity_score}, {dist:.1f} km away, roads {nearest.road_status})"
        )

        items.append(
            PriorityItem(
                entity=poi["name"],
                entity_type=poi["type"],
                lat=poi["lat"],
                lon=poi["lon"],
                priority_score=score,
                reason=reason,
            )
        )

    items.sort(key=lambda x: x.priority_score, reverse=True)
    return items
