"""
Agent 2 - Damage Assessment Agent

Purpose: estimate severity per sub-area. In production this runs YOLO/SAM/
SegFormer over satellite & drone imagery to detect building damage, flood
depth, fire spread, and road blockage. Here we simulate 3-5 affected zones
around the epicentre with severity driven by disaster type + a seeded RNG,
so results are deterministic and explainable for the same input.
"""
from typing import List
from backend.models.schemas import DisasterEvent, DamageReport
from backend.utils import jitter_point, seeded_random

SEVERITY_PROFILE = {
    "flood": {"buildings": (30, 85), "power_down_chance": 0.6},
    "earthquake": {"buildings": (50, 95), "power_down_chance": 0.7},
    "cyclone": {"buildings": (20, 70), "power_down_chance": 0.8},
    "fire": {"buildings": (40, 90), "power_down_chance": 0.4},
    "landslide": {"buildings": (35, 80), "power_down_chance": 0.5},
    "building_collapse": {"buildings": (60, 100), "power_down_chance": 0.3},
}


def assess(event: DisasterEvent) -> List[DamageReport]:
    rng = seeded_random(f"damage-{event.disaster_type}-{event.lat}-{event.lon}")
    profile = SEVERITY_PROFILE.get(event.disaster_type, SEVERITY_PROFILE["flood"])
    n_areas = rng.randint(3, 5)

    reports = []
    for i in range(n_areas):
        lat, lon = jitter_point(event.lat, event.lon, max_km=6.0)
        pct = round(rng.uniform(*profile["buildings"]), 1)
        road_roll = rng.random()
        road_status = "blocked" if road_roll < 0.3 else "partially_blocked" if road_roll < 0.65 else "open"
        power_status = "down" if rng.random() < profile["power_down_chance"] else "up"
        casualties = int(pct / 100 * rng.randint(5, 40))
        severity = round(pct * 0.6 + (30 if road_status == "blocked" else 10 if road_status == "partially_blocked" else 0) * 0.4, 1)

        reports.append(
            DamageReport(
                area_id=f"Area-{chr(65 + i)}",
                lat=lat,
                lon=lon,
                buildings_damaged_pct=pct,
                road_status=road_status,
                power_status=power_status,
                estimated_casualties=casualties,
                severity_score=min(severity, 100.0),
            )
        )
    return reports
