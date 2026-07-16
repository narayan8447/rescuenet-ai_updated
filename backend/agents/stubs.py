import json
from typing import Dict, Any

from backend.models.schemas import DisasterTriggerRequest
from backend.agents.graph_state import GraphState
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

def event_detection_node(state: GraphState) -> Dict[str, Any]:
    req = DisasterTriggerRequest(**state["raw_trigger"])
    event = event_detection.detect(req)
    return {"event": event}

def damage_assessment_node(state: GraphState) -> Dict[str, Any]:
    reports = damage_assessment.assess(state["event"])
    return {"damage_reports": reports}

def rescue_prioritization_node(state: GraphState) -> Dict[str, Any]:
    priorities = rescue_prioritization.prioritize(
        state["damage_reports"], state["live_state"]["points_of_interest"]
    )
    return {"priorities": priorities}

def resource_allocation_node(state: GraphState) -> Dict[str, Any]:
    assignments = resource_allocation.allocate(
        state["event"].disaster_type, state["priorities"], state["live_state"]["resources"]
    )
    return {"resource_assignments": assignments}

def route_optimization_node(state: GraphState) -> Dict[str, Any]:
    routes = route_optimization.plan_routes(
        state["resource_assignments"], state["priorities"], state["damage_reports"]
    )
    return {"routes": routes}

def hospital_capacity_node(state: GraphState) -> Dict[str, Any]:
    assignments = hospital_capacity.assign_patients(
        state["damage_reports"], state["live_state"]["hospitals"]
    )
    return {"hospital_assignments": assignments}

def shelter_allocation_node(state: GraphState) -> Dict[str, Any]:
    assignments = shelter_allocation.assign_shelters(
        state["damage_reports"], state["live_state"]["shelters"]
    )
    return {"shelter_assignments": assignments}

def relief_distribution_node(state: GraphState) -> Dict[str, Any]:
    plan = relief_distribution.plan_relief(state["shelter_assignments"])
    return {"relief_plan": plan}

def volunteer_coordination_node(state: GraphState) -> Dict[str, Any]:
    assignments = volunteer_coordination.assign_volunteers(
        state["priorities"], state["live_state"]["volunteers"]
    )
    return {"volunteer_assignments": assignments}

def communication_node(state: GraphState) -> Dict[str, Any]:
    alerts = communication.generate_alerts(state["event"], state["shelter_assignments"])
    return {"alerts": alerts}

def prediction_node(state: GraphState) -> Dict[str, Any]:
    forecasts = prediction.forecast(state["event"], state["damage_reports"])
    return {"forecasts": forecasts}

def situation_reporting_node(state: GraphState) -> Dict[str, Any]:
    narrative = situation_reporting.compile_summary(
        state["event"],
        state["damage_reports"],
        state["priorities"],
        state["resource_assignments"],
        state["routes"],
        state["hospital_assignments"],
        state["shelter_assignments"],
        state["relief_plan"],
        state["volunteer_assignments"],
        state["forecasts"],
    )
    return {"narrative_summary": narrative}
