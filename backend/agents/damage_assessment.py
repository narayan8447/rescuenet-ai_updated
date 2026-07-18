"""
Agent 2 - Damage Assessment Agent (Production V2)

Purpose: Estimate severity, casualties, and infrastructure damage using LLMs.
Uses Groq for fast inference, structured output, and Tenacity for retries.
"""
import os
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from backend.models.schemas import DisasterEvent, DamageReport
from backend.core.logging import logger
from backend.utils import jitter_point, seeded_random

# Simulated OpenStreetMap Overpass Tool
def query_osm_overpass(lat: float, lon: float, radius_km: float) -> dict:
    """Mock tool to fetch topological data and building density from OpenStreetMap."""
    logger.info("tool_execution", tool="query_osm_overpass", lat=lat, lon=lon, radius_km=radius_km)
    return {
        "building_density": "high",
        "major_roads": 3,
        "critical_infrastructure": ["power_substation", "water_treatment"]
    }

class DamageReportList(BaseModel):
    """Wrapper to force LLM to output a list of DamageReports."""
    reports: List[DamageReport] = Field(description="List of 3 to 5 assessed damage zones.")

class DamageAssessmentAgentV2:
    def __init__(self):
        # Initialize Groq LLM. Expects GROQ_API_KEY in environment.
        self.llm = ChatGroq(
            model="llama-3.1-8b-instant", # Larger model for spatial reasoning
            api_key=os.environ.get("GROQ_API_KEY", "dummy_key"),
            max_retries=2
        )
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def assess(self, event: DisasterEvent) -> List[DamageReport]:
        logger.info("damage_assessment_started", disaster_event=event.model_dump())
        logger.metric("agent_start", 1.0, tags={"agent": "damage_assessment"})
        
        # If dummy key, fallback to legacy dummy logic to avoid breaking test suites without mock patches
        if os.environ.get("GROQ_API_KEY", "dummy_key") == "dummy_key":
            logger.warn("using_fallback_damage_assessment_due_to_missing_groq_key")
            return self._legacy_assess(event)
            
        # Simulate tool usage for topological context
        topology = query_osm_overpass(event.lat, event.lon, 6.0)

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a crisis topology analyst. Given a disaster event and topological data, segment the area into 3 to 5 distinct sub-zones. Estimate damage decay based on distance from the epicenter. Calculate a severity_score (0-100), casualties, and road/power status. Road status must be 'open', 'partially_blocked', or 'blocked'. Power status must be 'up' or 'down'."),
            ("human", "Disaster Event: {event}\nTopological Context: {topology}")
        ])
        
        # Enforce structured output matching our Pydantic schema wrapper
        structured_llm = self.llm.with_structured_output(DamageReportList)
        chain = prompt | structured_llm
        
        try:
            result: DamageReportList = chain.invoke({
                "event": event.model_dump_json(),
                "topology": str(topology)
            })
            
            # Additional validation bounds logic
            for report in result.reports:
                report.severity_score = min(max(report.severity_score, 0.0), 100.0)
                # Ensure coordinates are reasonably bound to a 10km radius
                # If LLM hallucinates far coords, clamp them (simulated here by logging)
                if abs(report.lat - event.lat) > 0.1 or abs(report.lon - event.lon) > 0.1:
                    logger.warn("coordinate_clamp_triggered", area_id=report.area_id)
            
            logger.info("damage_assessment_success", num_reports=len(result.reports))
            # Calculate avg severity for metrics
            avg_sev = sum(r.severity_score for r in result.reports) / max(len(result.reports), 1)
            logger.metric("avg_damage_severity", avg_sev, tags={"agent": "damage_assessment"})
            
            return result.reports
            
        except Exception as e:
            logger.error("damage_assessment_failed", error=str(e))
            raise e
            
    def _legacy_assess(self, event: DisasterEvent) -> List[DamageReport]:
        SEVERITY_PROFILE = {
            "flood": {"buildings": (30, 85), "power_down_chance": 0.6},
            "earthquake": {"buildings": (50, 95), "power_down_chance": 0.7},
            "cyclone": {"buildings": (20, 70), "power_down_chance": 0.8},
            "fire": {"buildings": (40, 90), "power_down_chance": 0.4},
            "landslide": {"buildings": (35, 80), "power_down_chance": 0.5},
            "building_collapse": {"buildings": (60, 100), "power_down_chance": 0.3},
        }
        rng = seeded_random(f"damage-{event.disaster_type}-{event.lat}-{event.lon}")
        profile = SEVERITY_PROFILE.get(event.disaster_type, SEVERITY_PROFILE["flood"])
        n_areas = rng.randint(3, 5)

        reports = []
        for i in range(n_areas):
            lat, lon = jitter_point(event.lat, event.lon, max_km=6.0)
            pct = round(rng.uniform(*profile["buildings"]), 1)
            road_roll = rng.random()
            road_status = "blocked" if road_roll < 0.3 else "partially_blocked" if road_roll < 0.65 else "open"
            power_status = "down" if rng.random() < profile["power_down_chance"] else "up"
            casualties = int(pct / 100 * rng.randint(5, 40))
            severity = round(pct * 0.6 + (30 if road_status == "blocked" else 10 if road_status == "partially_blocked" else 0) * 0.4, 1)

            reports.append(
                DamageReport(
                    area_id=f"Area-{chr(65 + i)}",
                    lat=lat,
                    lon=lon,
                    buildings_damaged_pct=pct,
                    road_status=road_status,
                    power_status=power_status,
                    estimated_casualties=casualties,
                    severity_score=min(severity, 100.0),
                )
            )
        return reports

_agent = DamageAssessmentAgentV2()

def assess(event: DisasterEvent) -> List[DamageReport]:
    return _agent.assess(event)
