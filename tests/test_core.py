import pytest
from backend.core.state import GraphState
from backend.core.protocol import AgentMessage
from backend.core.base_agent import BaseAgent
from backend.core.registry import AgentRegistry
from backend.core.errors import DependencyResolutionError

class MockAgent(BaseAgent):
    name = "MockAgent"
    def execute(self, state: GraphState):
        return {"current_step": "mock_done"}

class MockFailingAgent(BaseAgent):
    name = "MockFailingAgent"
    def execute(self, state: GraphState):
        raise ValueError("Simulated failure")

def test_graph_state_initialization():
    state = GraphState()
    assert state.current_step == "supervisor"
    assert state.correlation_id is not None
    assert len(state.errors) == 0

def test_agent_message_protocol():
    msg = AgentMessage(
        sender="AgentA",
        receiver="AgentB",
        correlation_id="123",
        purpose="TEST",
        payload={"data": "test"},
        reasoning="Testing protocol",
        confidence=1.0
    )
    assert msg.sender == "AgentA"
    assert msg.status == "PENDING"
    assert msg.priority == "MEDIUM"

def test_agent_registry():
    AgentRegistry.clear()
    agent = MockAgent()
    AgentRegistry.register("mock", agent)
    
    retrieved = AgentRegistry.get("mock")
    assert retrieved is agent
    
    with pytest.raises(DependencyResolutionError):
        AgentRegistry.get("non_existent")

def test_base_agent_execution():
    agent = MockAgent()
    state = GraphState()
    result = agent.safe_execute(state)
    assert result["current_step"] == "mock_done"
