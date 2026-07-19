"""
Orchestrator Agent (Production V2)

Purpose: the "conductor" described in the architecture diagram.
This is a wrapper around the LangGraph V2 supervisor. Runs every
specialist agent, passes shared state between them, mutates the live 
resource/hospital/shelter pools, and records a step-by-step
trace so the frontend can show exactly what each agent decided and why.
"""
import uuid
from backend.models.schemas import DisasterTriggerRequest, AgentTrace, SituationReport
from backend.core.state import GraphState
from backend.agents.supervisor_v2 import supervisor_graph

def run_pipeline(req: DisasterTriggerRequest, state: dict) -> SituationReport:
    """Runs the full LangGraph multi-agent pipeline."""
    initial_state = GraphState(
        raw_trigger=req.model_dump(),
        live_state=state,
    ).model_dump()
    
    # Using a generated thread_id for the checkpoint memory
    thread_id = str(uuid.uuid4())
    # Limit max_concurrency to 3 to prevent OOM on Render by running fewer agents at exactly the same time.
    config = {"configurable": {"thread_id": thread_id}, "max_concurrency": 3}
    
    # Run until the first interruption or completion
    final_state = supervisor_graph.invoke(initial_state, config)
    
    # Generic loop to auto-resume on any Human-In-The-Loop interrupts until the graph is fully complete
    while True:
        state_info = supervisor_graph.get_state(config)
        if not state_info.next:
            break
        next_node = state_info.next[0]
        print(f"HITL: Interrupted at '{next_node}'. Simulating human approval and resuming...")
        final_state = supervisor_graph.invoke(None, config)
    
    # Handle both dict and Pydantic model returns
    if not isinstance(final_state, dict):
        final_state = final_state.model_dump()
        
    event = final_state.get("event")
    damage_reports = final_state.get("damage_reports", [])
    priorities = final_state.get("priorities", [])
    resource_assignments = final_state.get("resource_assignments", [])
    routes = final_state.get("routes", [])
    hospital_assignments = final_state.get("hospital_assignments", [])
    shelter_assignments = final_state.get("shelter_assignments", [])
    relief_plan = final_state.get("relief_plan", [])
    volunteer_assignments = final_state.get("volunteer_assignments", [])
    alerts = final_state.get("alerts", [])
    forecasts = final_state.get("forecasts", [])
    narrative_summary = final_state.get("narrative_summary", "Report generation failed.")

    # Reconstruct the trace list
    trace = []
    if event:
        trace.append(AgentTrace(agent="Event Detection (V2)", summary="Detected event", data=event))
    if damage_reports:
        trace.append(AgentTrace(agent="Damage Assessment (V2)", summary="Assessed damage", data=damage_reports))
    if priorities:
        trace.append(AgentTrace(agent="Rescue Prioritization (V2)", summary="Calculated priorities", data=priorities))
    if resource_assignments:
        trace.append(AgentTrace(agent="Resource Allocation (V2)", summary="Allocated resources", data=resource_assignments))
    if routes:
        trace.append(AgentTrace(agent="Route Optimization (V2)", summary="Calculated routes", data=routes))
    if hospital_assignments:
        trace.append(AgentTrace(agent="Hospital Capacity (V2)", summary="Assigned hospitals", data=hospital_assignments))
    if shelter_assignments:
        trace.append(AgentTrace(agent="Shelter Allocation (V2)", summary="Assigned shelters", data=shelter_assignments))
    if relief_plan:
        trace.append(AgentTrace(agent="Relief Distribution (V2)", summary="Planned relief", data=relief_plan))
    if volunteer_assignments:
        trace.append(AgentTrace(agent="Volunteer Coordination (V2)", summary="Coordinated volunteers", data=volunteer_assignments))
    if alerts:
        trace.append(AgentTrace(agent="Communication (V2)", summary="Generated alerts", data=alerts))
    if forecasts:
        trace.append(AgentTrace(agent="Prediction (V2)", summary="Generated forecasts", data=forecasts))
    
    trace.append(AgentTrace(agent="Situation Reporting (V2)", summary="Compiled final report", data={"narrative_summary": narrative_summary}))

    return SituationReport(
        event=event,
        damage_reports=damage_reports,
        priorities=priorities,
        resource_assignments=resource_assignments,
        routes=routes,
        hospital_assignments=hospital_assignments,
        shelter_assignments=shelter_assignments,
        relief_plan=relief_plan,
        volunteer_assignments=volunteer_assignments,
        alerts=alerts,
        forecasts=forecasts,
        narrative_summary=narrative_summary,
        trace=trace,
    )
