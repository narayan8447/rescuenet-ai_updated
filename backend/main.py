"""
RescueNet AI - FastAPI backend entrypoint.

Run with:
    uvicorn backend.main:app --reload --port 8000

Exposes the multi-agent pipeline as a REST API for the Streamlit dashboard
(or any other client / Postman / curl) to consume.
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from secure import Secure
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis
import os

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
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_methods=["*"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

secure_headers = Secure()
@app.middleware("http")
async def set_secure_headers(request, call_next):
    response = await call_next(request)
    secure_headers.set_headers(response)
    return response


@app.on_event("startup")
def startup():
    database.init_db()
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    redis_client = aioredis.from_url(redis_url)
    FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.0.0"}

@app.get("/")
def root():
    return {"message": "RescueNet AI backend is running. See /docs for the API."}

from backend.rag.api import router as rag_router
app.include_router(rag_router)

# OpenTelemetry Instrumentation
try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FastAPIInstrumentor.instrument_app(app)
except ImportError:
    pass

from backend.agents.supervisor_v2 import supervisor_graph
from backend.models.schemas import AgentTrace
from backend.core.logging import logger

@app.post("/api/disaster/trigger", response_model=SituationReport)
@limiter.limit("20/minute")
def trigger_disaster(request: Request, req: DisasterTriggerRequest):
    """Runs the full multi-agent pipeline for a newly reported disaster using LangGraph."""
    logger.info("disaster_triggered", type=req.disaster_type, location=req.location_name)
    logger.metric("pipeline_start", 1, tags={"type": req.disaster_type})
    
    report = orchestrator.run_pipeline(req, database.STATE)
    
    database.save_incident(req.disaster_type, req.location_name, report.model_dump())
    
    logger.info("disaster_processed", type=req.disaster_type, location=req.location_name)
    logger.metric("pipeline_complete", 1, tags={"type": req.disaster_type})
    return report



@app.get("/api/state")
@cache(expire=5)
def get_state():
    """Current live state of hospitals, shelters, resources, and volunteers."""
    return database.STATE

@app.get("/api/simulation/state")
def get_simulation_state():
    """Get the current state of the dynamic simulation."""
    return database.STATE

@app.post("/api/simulation/tick")
def tick_simulation(ticks: int = 1):
    """Fast forward the disaster simulation by N ticks."""
    database.advance_simulation(ticks)
    return {"message": f"Simulation advanced by {ticks} ticks.", "state": database.STATE}


@app.post("/api/reset")
def reset():
    """Resets hospitals/shelters/resources/volunteers back to defaults (does not touch history)."""
    database.reset_state()
    return {"message": "State reset to defaults."}


@app.get("/api/incidents")
@cache(expire=15)
def get_incidents(limit: int = 20):
    """History of past disaster triggers (long-term memory)."""
    return database.list_incidents(limit=limit)


@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: int):
    incident = database.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident
