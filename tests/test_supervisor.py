import pytest
import uuid
import os
os.environ["USE_FAKE_REDIS"] = "true"

from backend.core.state import GraphState
from backend.agents.supervisor_v2 import supervisor_graph

def test_supervisor_initial_routing():
    state = GraphState(raw_trigger={"disaster_type": "flood", "location_name": "Delhi NCR", "lat": 28.6, "lon": 77.2})
    
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    
    # We invoke it with a mocked event_detection to see where it routes? 
    # Actually, we can just test the whole graph's interruption on resource_allocation
    final_state = supervisor_graph.invoke(state, config)
    
    # It should interrupt before resource_allocation. 
    # We can verify it stopped by checking if it has a `next` state.
    current = supervisor_graph.get_state(config)
    assert len(current.next) > 0
    assert "resource_allocation" in current.next

    # Resume the graph by passing None for state
    final_state = supervisor_graph.invoke(None, config)
    
    # It should interrupt again before communication
    current = supervisor_graph.get_state(config)
    assert len(current.next) > 0
    assert "communication" in current.next

    # Resume again to finish the graph
    final_state = supervisor_graph.invoke(None, config)
    current = supervisor_graph.get_state(config)
    assert len(current.next) == 0
    
    # The final narrative summary should be generated
    assert final_state["narrative_summary"] is not None
