import json
from typing import Dict, Any

from backend.models.schemas import DisasterTriggerRequest
from backend.core.state import GraphState
from backend.core.base_agent import BaseAgent
from backend.core.registry import AgentRegistry

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

from backend.models.schemas import DisasterEvent, DamageReport, PriorityItem, ResourceAssignment, RouteInfo, HospitalAssignment, ShelterAssignment, VolunteerAssignment, ReliefPlan, Forecast, Alert

class EventDetectionAgent(BaseAgent):
    name = "event_detection"
    def execute(self, state: GraphState) -> Dict[str, Any]:
        req = DisasterTriggerRequest(**state.raw_trigger) if state.raw_trigger else None
        event = event_detection.detect(req)
        return {"event": event.model_dump() if event else None}

class DamageAssessmentAgent(BaseAgent):
    name = "damage_assessment"
    def execute(self, state: GraphState) -> Dict[str, Any]:
        event = DisasterEvent(**state.event) if state.event else None
        reports = damage_assessment.assess(event)
        return {"damage_reports": [r.model_dump() for r in reports]}

class RescuePrioritizationAgent(BaseAgent):
    name = "rescue_prioritization"
    def execute(self, state: GraphState) -> Dict[str, Any]:
        reports = [DamageReport(**r) for r in state.damage_reports]
        priorities = rescue_prioritization.prioritize(
            reports, state.live_state.get("points_of_interest", [])
        )
        return {"priorities": [p.model_dump() for p in priorities]}

class ResourceAllocationAgent(BaseAgent):
    name = "resource_allocation"
    def execute(self, state: GraphState) -> Dict[str, Any]:
        priorities = [PriorityItem(**p) for p in state.priorities]
        disaster_type = state.event.get("disaster_type", "unknown") if state.event else "unknown"
        assignments = resource_allocation.allocate(
            disaster_type, priorities, state.live_state.get("resources", {})
        )
        return {"resource_assignments": [a.model_dump() for a in assignments]}

class RouteOptimizationAgent(BaseAgent):
    name = "route_optimization"
    def execute(self, state: GraphState) -> Dict[str, Any]:
        assignments = [ResourceAssignment(**a) for a in state.resource_assignments]
        priorities = [PriorityItem(**p) for p in state.priorities]
        reports = [DamageReport(**r) for r in state.damage_reports]
        routes = route_optimization.plan_routes(assignments, priorities, reports)
        return {"routes": [r.model_dump() for r in routes]}

class HospitalCapacityAgent(BaseAgent):
    name = "hospital_capacity"
    def execute(self, state: GraphState) -> Dict[str, Any]:
        reports = [DamageReport(**r) for r in state.damage_reports]
        assignments = hospital_capacity.assign_patients(
            reports, state.live_state.get("hospitals", {})
        )
        return {"hospital_assignments": [a.model_dump() for a in assignments]}

class ShelterAllocationAgent(BaseAgent):
    name = "shelter_allocation"
    def execute(self, state: GraphState) -> Dict[str, Any]:
        reports = [DamageReport(**r) for r in state.damage_reports]
        assignments = shelter_allocation.assign_shelters(
            reports, state.live_state.get("shelters", {})
        )
        return {"shelter_assignments": [a.model_dump() for a in assignments]}

class ReliefDistributionAgent(BaseAgent):
    name = "relief_distribution"
    def execute(self, state: GraphState) -> Dict[str, Any]:
        assignments = [ShelterAssignment(**a) for a in state.shelter_assignments]
        plan = relief_distribution.plan_relief(assignments)
        return {"relief_plan": [p.model_dump() for p in plan]}

class VolunteerCoordinationAgent(BaseAgent):
    name = "volunteer_coordination"
    def execute(self, state: GraphState) -> Dict[str, Any]:
        priorities = [PriorityItem(**p) for p in state.priorities]
        assignments = volunteer_coordination.assign_volunteers(
            priorities, state.live_state.get("volunteers", {})
        )
        return {"volunteer_assignments": [a.model_dump() for a in assignments]}

class CommunicationAgent(BaseAgent):
    name = "communication"
    def execute(self, state: GraphState) -> Dict[str, Any]:
        event = DisasterEvent(**state.event) if state.event else None
        assignments = [ShelterAssignment(**a) for a in state.shelter_assignments]
        alerts = communication.generate_alerts(event, assignments)
        return {"alerts": [a.model_dump() for a in alerts]}

class PredictionAgent(BaseAgent):
    name = "prediction"
    def execute(self, state: GraphState) -> Dict[str, Any]:
        event = DisasterEvent(**state.event) if state.event else None
        reports = [DamageReport(**r) for r in state.damage_reports]
        forecasts = prediction.forecast(event, reports)
        return {"forecasts": [f.model_dump() for f in forecasts]}

class SituationReportingAgent(BaseAgent):
    name = "situation_reporting"
    def execute(self, state: GraphState) -> Dict[str, Any]:
        event = DisasterEvent(**state.event) if state.event else None
        reports = [DamageReport(**r) for r in state.damage_reports]
        priorities = [PriorityItem(**p) for p in state.priorities]
        r_assignments = [ResourceAssignment(**a) for a in state.resource_assignments]
        routes = [RouteInfo(**r) for r in state.routes]
        h_assignments = [HospitalAssignment(**a) for a in state.hospital_assignments]
        s_assignments = [ShelterAssignment(**a) for a in state.shelter_assignments]
        plan = [ReliefPlan(**p) for p in state.relief_plan]
        v_assignments = [VolunteerAssignment(**a) for a in state.volunteer_assignments]
        forecasts = [Forecast(**f) for f in state.forecasts]
        
        narrative = situation_reporting.compile_summary(
            event, reports, priorities, r_assignments, routes, h_assignments, s_assignments, plan, v_assignments, forecasts
        )
        return {"narrative_summary": narrative}

# Register all agents
AgentRegistry.register("event_detection", EventDetectionAgent())
AgentRegistry.register("damage_assessment", DamageAssessmentAgent())
AgentRegistry.register("rescue_prioritization", RescuePrioritizationAgent())
AgentRegistry.register("resource_allocation", ResourceAllocationAgent())
AgentRegistry.register("route_optimization", RouteOptimizationAgent())
AgentRegistry.register("hospital_capacity", HospitalCapacityAgent())
AgentRegistry.register("shelter_allocation", ShelterAllocationAgent())
AgentRegistry.register("relief_distribution", ReliefDistributionAgent())
AgentRegistry.register("volunteer_coordination", VolunteerCoordinationAgent())
AgentRegistry.register("communication", CommunicationAgent())
AgentRegistry.register("prediction", PredictionAgent())
AgentRegistry.register("situation_reporting", SituationReportingAgent())
