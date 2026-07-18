"""
Pydantic schemas shared by the API layer and the agents. These define the
"shape" of data that flows through the multi-agent pipeline, from the raw
disaster trigger all the way to the final situation report.

IMPORTANT: Every field that an LLM might produce as ``null`` is typed as
``Optional[...]`` with a sensible default.  Groq validates tool-call
arguments **before** returning them to us, so a required ``str`` field that
receives ``null`` causes an immediate ``tool_use_failed`` 400 error on
Groq's side – which we can never catch or retry.  Making the schema
tolerant is the only reliable fix.
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


class DisasterEvent(SafeBaseModel):
    disaster_type: Optional[str] = "unknown"
    location_name: Optional[str] = "unknown"
    lat: Optional[float] = 0.0
    lon: Optional[float] = 0.0
    confidence: Optional[float] = 0.0
    detected_at: Optional[str] = "unknown"


class DamageReport(SafeBaseModel):
    area_id: Optional[str] = "unknown"
    lat: Optional[float] = 0.0
    lon: Optional[float] = 0.0
    buildings_damaged_pct: Optional[float] = 0.0
    road_status: Optional[str] = "unknown"          # "open" | "partially_blocked" | "blocked"
    power_status: Optional[str] = "unknown"         # "up" | "down"
    estimated_casualties: Optional[int] = 0
    severity_score: Optional[float] = 0.0     # 0-100


class PriorityItem(SafeBaseModel):
    entity: Optional[str] = "unknown"
    entity_type: Optional[str] = "area"          # hospital | school | residential | warehouse | area
    lat: Optional[float] = 0.0
    lon: Optional[float] = 0.0
    priority_score: Optional[float] = 0.0
    reason: Optional[str] = "unspecified"


class ResourceAssignment(SafeBaseModel):
    resource_type: Optional[str] = "ambulance"
    resource_id: Optional[str] = None
    assigned_to: Optional[str] = "unassigned"
    distance_km: Optional[float] = 0.0
    eta_minutes: Optional[float] = 0.0


class RouteInfo(SafeBaseModel):
    resource_id: Optional[str] = None
    destination: Optional[str] = "unknown"
    distance_km: Optional[float] = 0.0
    status: Optional[str] = "clear"                # "clear" | "rerouted" | "delayed"
    note: Optional[str] = ""


class HospitalAssignment(SafeBaseModel):
    hospital_name: Optional[str] = "unknown"
    patients_assigned: Optional[int] = 0
    icu_beds_left: Optional[int] = 0
    general_beds_left: Optional[int] = 0
    status: Optional[str] = "unknown"


class ShelterAssignment(SafeBaseModel):
    shelter_name: Optional[str] = "unknown"
    people_assigned: Optional[int] = 0
    capacity_left: Optional[int] = 0
    distance_km: Optional[float] = 0.0


class ReliefPlan(SafeBaseModel):
    shelter_name: Optional[str] = "unknown"
    food_kits: Optional[int] = 0
    water_liters: Optional[int] = 0
    blankets: Optional[int] = 0
    medical_kits: Optional[int] = 0


class VolunteerAssignment(SafeBaseModel):
    volunteer_name: Optional[str] = "unknown"
    skill: Optional[str] = "general"
    assigned_task: Optional[str] = "unassigned"
    distance_km: Optional[float] = 0.0



class Alert(SafeBaseModel):
    language: Optional[str] = "en"
    channel: Optional[str] = "sms"
    message: Optional[str] = ""


class Forecast(SafeBaseModel):
    horizon_hours: Optional[int] = 0
    metric: Optional[str] = "unknown"
    predicted_value: Optional[float] = 0.0
    note: Optional[str] = ""


class AgentTrace(SafeBaseModel):
    agent: Optional[str] = "unknown"
    summary: Optional[str] = ""
    data: Any = None


class SituationReport(BaseModel):
    event: DisasterEvent
    damage_reports: List[DamageReport] = []
    priorities: List[PriorityItem] = []
    resource_assignments: List[ResourceAssignment] = []
    routes: List[RouteInfo] = []
    hospital_assignments: List[HospitalAssignment] = []
    shelter_assignments: List[ShelterAssignment] = []
    relief_plan: List[ReliefPlan] = []
    volunteer_assignments: List[VolunteerAssignment] = []
    alerts: List[Alert] = []
    forecasts: List[Forecast] = []
    narrative_summary: str = ""
    trace: List[AgentTrace] = []
