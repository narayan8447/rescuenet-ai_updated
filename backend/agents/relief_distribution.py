"""
Agent 8 - Relief Distribution Agent

Purpose: convert shelter headcounts into concrete supply requirements
(food, water, blankets, medical kits) using simple per-person standards,
so relief trucks know exactly what to load.
"""
from typing import List
from backend.models.schemas import ShelterAssignment, ReliefPlan

PER_PERSON_PER_DAY = {
    "food_kits": 1,       # 1 ready meal kit / person / day
    "water_liters": 4,    # WHO emergency minimum is ~3-5L/person/day
    "blankets": 0.5,       # 1 blanket per 2 people
    "medical_kits": 0.1,   # 1 basic kit per 10 people
}


def plan_relief(shelter_assignments: List[ShelterAssignment]) -> List[ReliefPlan]:
    plans = []
    for s in shelter_assignments:
        n = s.people_assigned
        if n <= 0:
            continue
        plans.append(
            ReliefPlan(
                shelter_name=s.shelter_name,
                food_kits=int(n * PER_PERSON_PER_DAY["food_kits"]),
                water_liters=int(n * PER_PERSON_PER_DAY["water_liters"]),
                blankets=int(n * PER_PERSON_PER_DAY["blankets"]) or 1,
                medical_kits=max(1, int(n * PER_PERSON_PER_DAY["medical_kits"])),
            )
        )
    return plans
