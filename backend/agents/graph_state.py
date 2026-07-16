from typing import TypedDict, List, Dict, Any, Optional
from backend.models.schemas import (
    DisasterEvent, DamageReport, PriorityItem, ResourceAssignment, RouteInfo,
    HospitalAssignment, ShelterAssignment, VolunteerAssignment, ReliefPlan,
    Forecast, Alert
)

class GraphState(TypedDict):
    """
    The universal state object passed between all LangGraph nodes.
    Combines orchestration metadata, live system state, and agent outputs.
    """
    # 1. ORCHESTRATION & EXECUTION METADATA
    raw_trigger: Dict[str, Any]
    current_step: str
    parallel_tasks: List[str]
    completed_tasks: List[str]
    errors: List[str]
    human_approved: bool

    # 2. LIVE DOMAIN STATE
    live_state: Dict[str, Any] # Contains hospitals, shelters, resources, etc (mocking Redis for now)

    # 3. AGENT GENERATED OUTPUTS
    event: Optional[DisasterEvent]
    damage_reports: List[DamageReport]
    priorities: List[PriorityItem]
    resource_assignments: List[ResourceAssignment]
    routes: List[RouteInfo]
    hospital_assignments: List[HospitalAssignment]
    shelter_assignments: List[ShelterAssignment]
    volunteer_assignments: List[VolunteerAssignment]
    relief_plan: List[ReliefPlan]
    forecasts: List[Forecast]
    alerts: List[Alert]
    narrative_summary: Optional[str]
