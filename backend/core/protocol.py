from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

class AgentMessage(BaseModel):
    """
    Universal Message Schema for Inter-Agent Communication Protocol (IACP).
    Used for event-driven asynchronous communication.
    """
    sender: str
    receiver: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str
    purpose: str
    payload: Dict[str, Any]
    reasoning: str
    confidence: float
    priority: str = "MEDIUM"
    status: str = "PENDING"
    required_actions: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
