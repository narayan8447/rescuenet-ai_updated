"""
Agent 7 - Shelter Allocation Agent

Purpose: estimate how many people are displaced and assign them to the
nearest shelters with remaining capacity. Mutates shared `shelters` state.
"""
from typing import List
from backend.models.schemas import DamageReport, ShelterAssignment
from backend.utils import haversine_km


def assign_shelters(damage_reports: List[DamageReport], shelters: list) -> List[ShelterAssignment]:
    # Rough displacement estimate: proportion of damaged buildings implies households displaced
    avg_damage_pct = sum(d.buildings_damaged_pct for d in damage_reports) / len(damage_reports)
    displaced_estimate = int(avg_damage_pct * 12)  # simulated multiplier -> people needing shelter

    epicentre_lat = sum(d.lat for d in damage_reports) / len(damage_reports)
    epicentre_lon = sum(d.lon for d in damage_reports) / len(damage_reports)

    ranked = sorted(shelters, key=lambda s: haversine_km(epicentre_lat, epicentre_lon, s["lat"], s["lon"]))

    assignments = []
    remaining = displaced_estimate
    for s in ranked:
        if remaining <= 0:
            break
        take = min(remaining, s["capacity"])
        s["capacity"] -= take
        remaining -= take
        dist = haversine_km(epicentre_lat, epicentre_lon, s["lat"], s["lon"])
        assignments.append(
            ShelterAssignment(
                shelter_name=s["name"],
                people_assigned=take,
                capacity_left=s["capacity"],
                distance_km=round(dist, 2),
            )
        )
    return assignments
