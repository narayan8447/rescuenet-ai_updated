"""
Orchestrator Agent

Purpose: the "conductor" described in the architecture diagram. Runs every
specialist agent in the correct order, passes shared state between them,
mutates the live resource/hospital/shelter pools, and records a step-by-step
trace so the frontend can show exactly what each agent decided and why.

Pipeline (matches the brief's workflow diagram):
Event Detection -> Damage Assessment -> Rescue Prioritization ->
Resource Allocation -> Route Optimization -> Hospital Capacity ->
Shelter Allocation -> Relief Distribution -> Volunteer Coordination ->
Communication -> Prediction -> Situation Reporting
"""
from backend.models.schemas import DisasterTriggerRequest, AgentTrace, SituationReport
from backend.agents import (
    event_detection,
    damage_assessment,
    rescue_prioritization,
    resource_allocation,
    route_optimization,
    hospital_capacity,
    shelter_allocation,
    relief_distribution,
    volunteer_coordination,
    communication,
    prediction,
    situation_reporting,
)


def run_pipeline(req: DisasterTriggerRequest, state: dict) -> SituationReport:
    trace = []

    event = event_detection.detect(req)
    trace.append(AgentTrace(agent="Event Detection Agent",
                             summary=f"Confirmed {event.disaster_type} at {event.location_name} (confidence {event.confidence*100:.1f}%).",
                             data=event.model_dump()))

    damage_reports = damage_assessment.assess(event)
    trace.append(AgentTrace(agent="Damage Assessment Agent",
                             summary=f"Assessed {len(damage_reports)} zones; avg damage {sum(d.buildings_damaged_pct for d in damage_reports)/len(damage_reports):.1f}%.",
                             data=[d.model_dump() for d in damage_reports]))

    priorities = rescue_prioritization.prioritize(damage_reports, state["points_of_interest"])
    trace.append(AgentTrace(agent="Rescue Prioritization Agent",
                             summary=f"Ranked {len(priorities)} locations; top priority: {priorities[0].entity if priorities else 'N/A'}.",
                             data=[p.model_dump() for p in priorities]))

    resource_assignments = resource_allocation.allocate(event.disaster_type, priorities, state["resources"])
    trace.append(AgentTrace(agent="Resource Allocation Agent",
                             summary=f"Dispatched {len(resource_assignments)} resources to top-priority locations.",
                             data=[r.model_dump() for r in resource_assignments]))

    routes = route_optimization.plan_routes(resource_assignments, priorities, damage_reports)
    trace.append(AgentTrace(agent="Route Optimization Agent",
                             summary=f"Planned {len(routes)} routes; {sum(1 for r in routes if r.status != 'clear')} required rerouting/delay.",
                             data=[r.model_dump() for r in routes]))

    hospital_assignments = hospital_capacity.assign_patients(damage_reports, state["hospitals"])
    trace.append(AgentTrace(agent="Hospital Capacity Agent",
                             summary=f"Assigned patients across {len(hospital_assignments)} hospitals.",
                             data=[h.model_dump() for h in hospital_assignments]))

    shelter_assignments = shelter_allocation.assign_shelters(damage_reports, state["shelters"])
    trace.append(AgentTrace(agent="Shelter Allocation Agent",
                             summary=f"Assigned {sum(s.people_assigned for s in shelter_assignments)} displaced people across {len(shelter_assignments)} shelters.",
                             data=[s.model_dump() for s in shelter_assignments]))

    relief_plan = relief_distribution.plan_relief(shelter_assignments)
    trace.append(AgentTrace(agent="Relief Distribution Agent",
                             summary=f"Calculated relief supply requirements for {len(relief_plan)} shelters.",
                             data=[r.model_dump() for r in relief_plan]))

    volunteer_assignments = volunteer_coordination.assign_volunteers(priorities, state["volunteers"])
    trace.append(AgentTrace(agent="Volunteer Coordination Agent",
                             summary=f"Activated {len(volunteer_assignments)} volunteers.",
                             data=[v.model_dump() for v in volunteer_assignments]))

    alerts = communication.generate_alerts(event, shelter_assignments)
    trace.append(AgentTrace(agent="Communication Agent",
                             summary=f"Generated {len(alerts)} public alert messages across languages/channels.",
                             data=[a.model_dump() for a in alerts]))

    forecasts = prediction.forecast(event, damage_reports)
    trace.append(AgentTrace(agent="Prediction Agent",
                             summary=f"Produced {len(forecasts)} forecasts for the next 6-24 hours.",
                             data=[f.model_dump() for f in forecasts]))

    narrative = situation_reporting.compile_summary(
        event, damage_reports, priorities, resource_assignments, routes,
        hospital_assignments, shelter_assignments, relief_plan,
        volunteer_assignments, forecasts,
    )
    trace.append(AgentTrace(agent="Situation Reporting Agent",
                             summary="Compiled final situation report.",
                             data={"narrative_summary": narrative}))

    return SituationReport(
        event=event,
        damage_reports=damage_reports,
        priorities=priorities,
        resource_assignments=resource_assignments,
        routes=routes,
        hospital_assignments=hospital_assignments,
        shelter_assignments=shelter_assignments,
        relief_plan=relief_plan,
        volunteer_assignments=volunteer_assignments,
        alerts=alerts,
        forecasts=forecasts,
        narrative_summary=narrative,
        trace=trace,
    )
