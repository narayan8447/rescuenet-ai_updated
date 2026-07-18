"""
Pydantic schemas shared by the API layer and the agents. These define the
"shape" of data that flows through the multi-agent pipeline, from the raw
disaster trigger all the way to the final situation report.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator

class SafeBaseModel(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def clean_none_strings(cls, data: Any) -> Any:
        if isinstance(data, dict):
            cleaned = {}
            for k, v in data.items():
                if isinstance(v, str) and v.strip().lower() in ("none", "null", "n/a", ""):
                    cleaned[k] = None
                else:
                    cleaned[k] = v
            return cleaned
        return data



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


class ResourceAssignment(SafeBaseModel):
    resource_type: str
    resource_id: Optional[str] = None
    assigned_to: str
    distance_km: Optional[float] = 0.0
    eta_minutes: Optional[float] = 0.0


class RouteInfo(SafeBaseModel):
    resource_id: Optional[str] = None
    destination: str
    distance_km: Optional[float] = 0.0
    status: str                # "clear" | "rerouted" | "delayed"
    note: str


class HospitalAssignment(SafeBaseModel):
    hospital_name: str
    patients_assigned: Optional[int] = 0
    icu_beds_left: Optional[int] = 0
    general_beds_left: Optional[int] = 0
    status: str


class ShelterAssignment(SafeBaseModel):
    shelter_name: str
    people_assigned: Optional[int] = 0
    capacity_left: Optional[int] = 0
    distance_km: Optional[float] = 0.0


class ReliefPlan(SafeBaseModel):
    shelter_name: str
    food_kits: Optional[int] = 0
    water_liters: Optional[int] = 0
    blankets: Optional[int] = 0
    medical_kits: Optional[int] = 0


class VolunteerAssignment(SafeBaseModel):
    volunteer_name: str
    skill: str
    assigned_task: str
    distance_km: Optional[float] = 0.0



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
