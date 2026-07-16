"""
RescueNet AI - FastAPI backend entrypoint.

Run with:
    uvicorn backend.main:app --reload --port 8000

Exposes the multi-agent pipeline as a REST API for the Streamlit dashboard
(or any other client / Postman / curl) to consume.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.models.schemas import DisasterTriggerRequest, SituationReport
from backend.agents import orchestrator
from backend import database

app = FastAPI(
    title="RescueNet AI",
    description="Multi-agent disaster response command center (academic simulation project).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    database.init_db()


@app.get("/")
def root():
    return {"message": "RescueNet AI backend is running. See /docs for the API."}


from backend.agents.supervisor_v2 import supervisor_graph
from backend.models.schemas import AgentTrace

@app.post("/api/disaster/trigger", response_model=SituationReport)
def trigger_disaster(req: DisasterTriggerRequest):
    """Runs the full multi-agent pipeline for a newly reported disaster using LangGraph."""
    
    initial_state = {
        "raw_trigger": req.model_dump(),
        "live_state": database.STATE,
    }
    
    # Execute the LangGraph supervisor workflow
    final_state = supervisor_graph.invoke(initial_state)
    
    # Reconstruct the SituationReport (maintaining compatibility with frontend)
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
        trace.append(AgentTrace(agent="Event Detection (V2)", summary="Detected event", data=event.model_dump()))
    if damage_reports:
        trace.append(AgentTrace(agent="Damage Assessment (V2)", summary="Assessed damage", data=[d.model_dump() for d in damage_reports]))
    if priorities:
        trace.append(AgentTrace(agent="Rescue Prioritization (V2)", summary="Calculated priorities", data=[p.model_dump() for p in priorities]))
    if resource_assignments:
        trace.append(AgentTrace(agent="Resource Allocation (V2)", summary="Allocated resources", data=[r.model_dump() for r in resource_assignments]))
    if routes:
        trace.append(AgentTrace(agent="Route Optimization (V2)", summary="Calculated routes", data=[r.model_dump() for r in routes]))
    if hospital_assignments:
        trace.append(AgentTrace(agent="Hospital Capacity (V2)", summary="Assigned hospitals", data=[h.model_dump() for h in hospital_assignments]))
    if shelter_assignments:
        trace.append(AgentTrace(agent="Shelter Allocation (V2)", summary="Assigned shelters", data=[s.model_dump() for s in shelter_assignments]))
    if relief_plan:
        trace.append(AgentTrace(agent="Relief Distribution (V2)", summary="Planned relief", data=[r.model_dump() for r in relief_plan]))
    if volunteer_assignments:
        trace.append(AgentTrace(agent="Volunteer Coordination (V2)", summary="Coordinated volunteers", data=[v.model_dump() for v in volunteer_assignments]))
    if alerts:
        trace.append(AgentTrace(agent="Communication (V2)", summary="Generated alerts", data=[a.model_dump() for a in alerts]))
    if forecasts:
        trace.append(AgentTrace(agent="Prediction (V2)", summary="Generated forecasts", data=[f.model_dump() for f in forecasts]))
    
    trace.append(AgentTrace(agent="Situation Reporting (V2)", summary="Compiled final report", data={"narrative_summary": narrative_summary}))

    report = SituationReport(
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
    
    database.save_incident(req.disaster_type, req.location_name, report.model_dump())
    return report



@app.get("/api/state")
def get_state():
    """Current live state of hospitals, shelters, resources, and volunteers."""
    return database.STATE


@app.post("/api/reset")
def reset():
    """Resets hospitals/shelters/resources/volunteers back to defaults (does not touch history)."""
    database.reset_state()
    return {"message": "State reset to defaults."}


@app.get("/api/incidents")
def get_incidents(limit: int = 20):
    """History of past disaster triggers (long-term memory)."""
    return database.list_incidents(limit=limit)


@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: int):
    incident = database.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident
