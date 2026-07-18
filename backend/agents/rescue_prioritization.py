"""
Agent 3 - Rescue Prioritization Agent (Production V2)

Purpose: Answer "who gets rescued first?" by scoring points of interest
against nearby damage severity, facility criticality, and population weight.
Uses Groq LLM for intelligent triaging and reasoning.
"""
import os
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from backend.models.schemas import DamageReport, PriorityItem
from backend.core.logging import logger
from backend.utils import haversine_km

# Simulated Tool for fetching facility history/vulnerability
def fetch_infrastructure_vulnerability(entity_name: str) -> dict:
    """Mock tool to fetch structural vulnerability score of an entity."""
    logger.info("tool_execution", tool="fetch_infrastructure_vulnerability", entity=entity_name)
    return {"structural_vulnerability": "high", "has_backup_power": False}

class PriorityItemList(BaseModel):
    """Wrapper to force LLM to output a list of PriorityItems."""
    priorities: List[PriorityItem] = Field(description="Ranked list of priorities.")

class RescuePrioritizationAgentV2:
    def __init__(self):
        self.llm = ChatGroq(
            model="groq/compound-mini",
            api_key=os.environ.get("GROQ_API_KEY", "dummy_key"),
            max_retries=2
        )
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def prioritize(self, damage_reports: List[DamageReport], points_of_interest: list) -> List[PriorityItem]:
        logger.info("rescue_prioritization_started", num_reports=len(damage_reports), num_pois=len(points_of_interest))
        logger.metric("agent_start", 1.0, tags={"agent": "rescue_prioritization"})
        
        if not points_of_interest:
            logger.warn("no_points_of_interest_provided")
            return []
            
        if os.environ.get("GROQ_API_KEY", "dummy_key") == "dummy_key":
            logger.warn("using_fallback_rescue_prioritization_due_to_missing_groq_key")
            return self._legacy_prioritize(damage_reports, points_of_interest)
            
        # Simulate tool usage
        fetch_infrastructure_vulnerability(points_of_interest[0].get("name", "Unknown"))
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert search and rescue commander. Triaging multiple points of interest based on nearby damage severity, facility criticality (e.g., hospitals > schools > residential), and population weight. Score each from 0.0 to 100.0. Provide a short reason explaining the score incorporating distance to damage, facility type, and severity. Output must strictly match the schema."),
            ("human", "Damage Reports: {reports}\nPoints of Interest: {pois}")
        ])
        
        structured_llm = self.llm.with_structured_output(PriorityItemList)
        chain = prompt | structured_llm
        
        try:
            reports_json = [r.model_dump() for r in damage_reports]
            result: PriorityItemList = chain.invoke({
                "reports": reports_json,
                "pois": points_of_interest
            })
            
            # Post-process: Sort and validate bounds
            items = result.priorities
            for item in items:
                item.priority_score = min(max(item.priority_score, 0.0), 100.0)
                
            items.sort(key=lambda x: x.priority_score, reverse=True)
            
            logger.info("rescue_prioritization_success", num_prioritized=len(items))
            if items:
                logger.metric("max_priority_score", items[0].priority_score, tags={"agent": "rescue_prioritization"})
                
            return items
            
        except Exception as e:
            logger.error("rescue_prioritization_failed", error=str(e))
            raise e
            
    def _legacy_prioritize(self, damage_reports: List[DamageReport], points_of_interest: list) -> List[PriorityItem]:
        TYPE_BASE_SCORE = {
            "hospital": 100,
            "school": 90,
            "residential": 70,
            "warehouse": 40,
        }
        items = []
        for poi in points_of_interest:
            base = TYPE_BASE_SCORE.get(poi.get("type", "residential"), 50)
            
            nearest = min(
                damage_reports,
                key=lambda d: haversine_km(poi["lat"], poi["lon"], d.lat, d.lon),
            )
            dist = haversine_km(poi["lat"], poi["lon"], nearest.lat, nearest.lon)
            proximity_factor = max(0.0, 1 - dist / 10)
            
            score = base * 0.5 + nearest.severity_score * 0.35 * proximity_factor + poi.get("population_weight", 0.5) * 15
            score = round(min(score, 100.0), 1)
            
            reason = (
                f"{poi.get('type', 'Unknown').title()} near {nearest.area_id} "
                f"(severity {nearest.severity_score}, {dist:.1f} km away, roads {nearest.road_status})"
            )
            
            items.append(
                PriorityItem(
                    entity=poi.get("name", "Unknown"),
                    entity_type=poi.get("type", "residential"),
                    lat=poi["lat"],
                    lon=poi["lon"],
                    priority_score=score,
                    reason=reason,
                )
            )
            
        items.sort(key=lambda x: x.priority_score, reverse=True)
        return items

_agent = RescuePrioritizationAgentV2()

def prioritize(damage_reports: List[DamageReport], points_of_interest: list) -> List[PriorityItem]:
    return _agent.prioritize(damage_reports, points_of_interest)
