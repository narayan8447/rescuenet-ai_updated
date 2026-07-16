"""
Agent 11 - Situation Reporting Agent

Purpose: compile every other agent's output into one human-readable
narrative summary for government dashboards / media briefings, plus the
structured SituationReport object the frontend renders.
"""
from typing import List
from backend.models.schemas import (
    DisasterEvent, DamageReport, PriorityItem, ResourceAssignment, RouteInfo,
    HospitalAssignment, ShelterAssignment, ReliefPlan, VolunteerAssignment,
    Alert, Forecast,
)


def compile_summary(
    event: DisasterEvent,
    damage_reports: List[DamageReport],
    priorities: List[PriorityItem],
    resource_assignments: List[ResourceAssignment],
    routes: List[RouteInfo],
    hospital_assignments: List[HospitalAssignment],
    shelter_assignments: List[ShelterAssignment],
    relief_plan: List[ReliefPlan],
    volunteer_assignments: List[VolunteerAssignment],
    forecasts: List[Forecast],
) -> str:
    total_casualties = sum(d.estimated_casualties for d in damage_reports)
    total_displaced = sum(s.people_assigned for s in shelter_assignments)
    top_priority = priorities[0].entity if priorities else "N/A"
    rerouted = sum(1 for r in routes if r.status != "clear")

    lines = [
        f"{event.disaster_type.replace('_', ' ').title()} detected in {event.location_name} "
        f"(confidence {event.confidence * 100:.1f}%).",
        f"{len(damage_reports)} affected zones identified, with an estimated {total_casualties} casualties requiring assistance.",
        f"Highest-priority response target: {top_priority}.",
        f"{len(resource_assignments)} emergency resources dispatched; {rerouted} of {len(routes)} routes required rerouting or delay due to road conditions.",
        f"{sum(h.patients_assigned for h in hospital_assignments)} patients assigned across {len(hospital_assignments)} hospitals.",
        f"{total_displaced} people assigned to shelters across {len(shelter_assignments)} sites; relief supplies calculated for all active shelters.",
        f"{len(volunteer_assignments)} volunteers activated to support field teams.",
    ]
    if forecasts:
        demand_forecast = next((f for f in forecasts if f.metric == "hospital_admission_demand"), None)
        if demand_forecast:
            lines.append(
                f"Forecast: an additional ~{int(demand_forecast.predicted_value)} hospital admissions expected within 24 hours if conditions continue."
            )
    return " ".join(lines)
