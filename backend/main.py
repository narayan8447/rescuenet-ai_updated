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


@app.post("/api/disaster/trigger", response_model=SituationReport)
def trigger_disaster(req: DisasterTriggerRequest):
    """Runs the full multi-agent pipeline for a newly reported disaster."""
    report = orchestrator.run_pipeline(req, database.STATE)
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
