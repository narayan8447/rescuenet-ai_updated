from langgraph.graph import StateGraph, END
from typing import List, Union

from backend.agents.graph_state import GraphState
from backend.agents.stubs import (
    event_detection_node,
    damage_assessment_node,
    rescue_prioritization_node,
    resource_allocation_node,
    route_optimization_node,
    hospital_capacity_node,
    shelter_allocation_node,
    relief_distribution_node,
    volunteer_coordination_node,
    communication_node,
    prediction_node,
    situation_reporting_node,
)

def supervisor_node(state: GraphState):
    # The supervisor doesn't mutate state itself, it just exists as a hub
    # for the conditional edges to evaluate the state.
    return {}

def route_supervisor(state: GraphState) -> Union[str, List[str]]:
    """Determine which node(s) should run next based on what's missing in the state."""
    if state.get("event") is None:
        return "event_detection"
    if not state.get("damage_reports"):
        return "damage_assessment"
    if not state.get("priorities"):
        return "rescue_prioritization"
    if not state.get("resource_assignments"):
        return "resource_allocation"

    
    # Parallel Fan-Out Block
    parallel_targets = []
    if not state.get("routes"):
        parallel_targets.append("route_optimization")
    if not state.get("hospital_assignments"):
        parallel_targets.append("hospital_capacity")
    if not state.get("shelter_assignments"):
        parallel_targets.append("shelter_allocation")
    if not state.get("volunteer_assignments"):
        parallel_targets.append("volunteer_coordination")
    
    if parallel_targets:
        return parallel_targets

    # Dependent Nodes
    if not state.get("relief_plan"):
        return "relief_distribution"
    if not state.get("forecasts"):
        return "prediction"
    if not state.get("alerts"):
        return "communication"
    if state.get("narrative_summary") is None:
        return "situation_reporting"
    
    return END

def build_supervisor_graph():
    builder = StateGraph(GraphState)

    # Add all nodes
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("event_detection", event_detection_node)
    builder.add_node("damage_assessment", damage_assessment_node)
    builder.add_node("rescue_prioritization", rescue_prioritization_node)
    builder.add_node("resource_allocation", resource_allocation_node)
    builder.add_node("route_optimization", route_optimization_node)
    builder.add_node("hospital_capacity", hospital_capacity_node)
    builder.add_node("shelter_allocation", shelter_allocation_node)
    builder.add_node("relief_distribution", relief_distribution_node)
    builder.add_node("volunteer_coordination", volunteer_coordination_node)
    builder.add_node("communication", communication_node)
    builder.add_node("prediction", prediction_node)
    builder.add_node("situation_reporting", situation_reporting_node)

    # Set Entry Point
    builder.set_entry_point("supervisor")

    # Add Edges (Spokes -> Hub)
    # Every specialist node returns control to the supervisor
    for node in [
        "event_detection", "damage_assessment", "rescue_prioritization",
        "resource_allocation", "route_optimization", "hospital_capacity",
        "shelter_allocation", "relief_distribution", "volunteer_coordination",
        "communication", "prediction", "situation_reporting"
    ]:
        builder.add_edge(node, "supervisor")

    # Add Conditional Edges (Hub -> Spokes)
    builder.add_conditional_edges(
        "supervisor",
        route_supervisor,
    )

    # Compile the graph
    return builder.compile()

# Instantiate the globally available graph
supervisor_graph = build_supervisor_graph()
