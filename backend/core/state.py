from typing import List, Dict, Any, Optional, Annotated
from pydantic import BaseModel, Field
import uuid
import operator

class GraphState(BaseModel):
    """
    The universal state object passed between all LangGraph nodes.
    Combines orchestration metadata, live system state, and agent outputs.
    """
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    current_step: str = Field(default="supervisor")
    supervisor_plan: List[str] = Field(default_factory=list)
    parallel_tasks: List[str] = Field(default_factory=list)
    completed_tasks: Annotated[List[str], operator.add] = Field(default_factory=list)
    execution_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    errors: List[str] = Field(default_factory=list)
    retries: Dict[str, int] = Field(default_factory=dict)
    human_approvals: Dict[str, bool] = Field(default_factory=dict)

    memory_references: List[Dict[str, Any]] = Field(default_factory=list)
    live_state: Dict[str, Any] = Field(default_factory=dict)

    raw_trigger: Optional[Dict[str, Any]] = None
    event: Optional[Dict[str, Any]] = None
    damage_reports: List[Dict[str, Any]] = Field(default_factory=list)
    priorities: List[Dict[str, Any]] = Field(default_factory=list)
    resource_assignments: List[Dict[str, Any]] = Field(default_factory=list)
    routes: List[Dict[str, Any]] = Field(default_factory=list)
    hospital_assignments: List[Dict[str, Any]] = Field(default_factory=list)
    shelter_assignments: List[Dict[str, Any]] = Field(default_factory=list)
    volunteer_assignments: List[Dict[str, Any]] = Field(default_factory=list)
    relief_plan: List[Dict[str, Any]] = Field(default_factory=list)
    forecasts: List[Dict[str, Any]] = Field(default_factory=list)
    alerts: List[Dict[str, Any]] = Field(default_factory=list)
    narrative_summary: Optional[str] = None

    streaming_events: List[Dict[str, Any]] = Field(default_factory=list)
    last_checkpoint: Optional[str] = None
