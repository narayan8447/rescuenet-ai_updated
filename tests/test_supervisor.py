import pytest
from backend.agents.supervisor_v2 import route_supervisor
from backend.agents.graph_state import GraphState

def test_supervisor_initial_routing():
    state = GraphState(raw_trigger={"disaster_type": "flood", "location_name": "Delhi NCR", "lat": 28.6, "lon": 77.2})
    
    # Missing event -> should route to event_detection
    next_node = route_supervisor(state)
    assert next_node == "event_detection"

def test_supervisor_parallel_fanout():
    state = GraphState(
        raw_trigger={},
        event={"disaster_type": "flood"},
        damage_reports=[{"area_id": "A"}],
        priorities=[{"entity": "B"}],
        resource_assignments=[{"resource_id": "AMB-01"}]
    )
    
    # Should fan out to 4 parallel nodes
    next_nodes = route_supervisor(state)
    assert isinstance(next_nodes, list)
    assert "route_optimization" in next_nodes
    assert "hospital_capacity" in next_nodes
    assert "shelter_allocation" in next_nodes
    assert "volunteer_coordination" in next_nodes

def test_supervisor_end_state():
    state = GraphState(
        raw_trigger={},
        event={},
        damage_reports=[{}],
        priorities=[{}],
        resource_assignments=[{}],
        routes=[{}],
        hospital_assignments=[{}],
        shelter_assignments=[{}],
        volunteer_assignments=[{}],
        relief_plan=[{}],
        forecasts=[{}],
        alerts=[{}],
        narrative_summary="Final Report"
    )
    
    next_node = route_supervisor(state)
    assert next_node == "__end__"
