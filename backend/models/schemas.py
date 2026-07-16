"""
Pydantic schemas shared by the API layer and the agents. These define the
"shape" of data that flows through the multi-agent pipeline, from the raw
disaster trigger all the way to the final situation report.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DisasterTriggerRequest(BaseModel):
    disaster_type: str = Field(..., description="flood | earthquake | cyclone | fire | landslide | building_collapse")
    location_name: str
    lat: float
    lon: float
    reported_by: Optional[str] = "citizen_report"


class DisasterEvent(BaseModel):
    disaster_type: str
    location_name: str
    lat: float
    lon: float
    confidence: float
    detected_at: str


class DamageReport(BaseModel):
    area_id: str
    lat: float
    lon: float
    buildings_damaged_pct: float
    road_status: str          # "open" | "partially_blocked" | "blocked"
    power_status: str         # "up" | "down"
    estimated_casualties: int
    severity_score: float     # 0-100


class PriorityItem(BaseModel):
    entity: str
    entity_type: str          # hospital | school | residential | warehouse | area
    lat: float
    lon: float
    priority_score: float
    reason: str


class ResourceAssignment(BaseModel):
    resource_type: str
    resource_id: str
    assigned_to: str
    distance_km: float
    eta_minutes: float


class RouteInfo(BaseModel):
    resource_id: str
    destination: str
    distance_km: float
    status: str                # "clear" | "rerouted" | "delayed"
    note: str


class HospitalAssignment(BaseModel):
    hospital_name: str
    patients_assigned: int
    icu_beds_left: int
    general_beds_left: int
    status: str


class ShelterAssignment(BaseModel):
    shelter_name: str
    people_assigned: int
    capacity_left: int
    distance_km: float


class ReliefPlan(BaseModel):
    shelter_name: str
    food_kits: int
    water_liters: int
    blankets: int
    medical_kits: int


class VolunteerAssignment(BaseModel):
    volunteer_name: str
    skill: str
    assigned_task: str
    distance_km: float


class Alert(BaseModel):
    language: str
    channel: str
    message: str


class Forecast(BaseModel):
    horizon_hours: int
    metric: str
    predicted_value: float
    note: str


class AgentTrace(BaseModel):
    agent: str
    summary: str
    data: Any


class SituationReport(BaseModel):
    event: DisasterEvent
    damage_reports: List[DamageReport]
    priorities: List[PriorityItem]
    resource_assignments: List[ResourceAssignment]
    routes: List[RouteInfo]
    hospital_assignments: List[HospitalAssignment]
    shelter_assignments: List[ShelterAssignment]
    relief_plan: List[ReliefPlan]
    volunteer_assignments: List[VolunteerAssignment]
    alerts: List[Alert]
    forecasts: List[Forecast]
    narrative_summary: str
    trace: List[AgentTrace]
