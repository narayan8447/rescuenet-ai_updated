"""
Agent 7 - Shelter Allocation Agent (Production V2)

Purpose: Estimates displaced populations and dynamically assigns them to the
nearest available shelters using LLM logic. Mutates shared `shelters` state.
"""
import os
import time
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential
from backend.core.llm_pool import get_google_llm
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from backend.models.schemas import DamageReport, ShelterAssignment
from backend.core.logging import logger
from backend.utils import haversine_km
from backend.core.memory import memory_manager

class ShelterAssignmentList(BaseModel):
    """Wrapper to force LLM to output a list of ShelterAssignments."""
    assignments: List[ShelterAssignment] = Field(description="List of shelter assignments for displaced persons.")

# Simulated Tool
def check_shelter_conditions(shelter_name: str) -> dict:
    """Mock tool to simulate checking real-time shelter supplies (food/water)."""
    logger.info("tool_execution", tool="check_shelter_conditions", shelter=shelter_name)
    return {"supplies_status": "nominal", "heating_active": True}

class ShelterAllocationAgentV2:
    def __init__(self):
        self.llm = get_google_llm()
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def assign_shelters(self, damage_reports: List[DamageReport], shelters: list) -> List[ShelterAssignment]:
        logger.info("shelter_allocation_started", num_reports=len(damage_reports), num_shelters=len(shelters))
        logger.metric("agent_start", 1.0, tags={"agent": "shelter_allocation"})
        
        if not shelters or not damage_reports:
            return []
            
        if os.environ.get("GOOGLE_API_KEY", "dummy_key") == "dummy_key":
            logger.warn("using_fallback_shelter_allocation_due_to_missing_google_key")
            return self._legacy_assign_shelters(damage_reports, shelters)
            
        # Rough displacement estimate: proportion of damaged buildings implies households displaced
        avg_damage_pct = sum(d.buildings_damaged_pct for d in damage_reports) / len(damage_reports)
        displaced_estimate = int(avg_damage_pct * 12)  # simulated multiplier -> people needing shelter
        
        epicentre_lat = sum(d.lat for d in damage_reports) / len(damage_reports)
        epicentre_lon = sum(d.lon for d in damage_reports) / len(damage_reports)
        
        # Sort shelters by proximity to epicentre
        ranked_shelters = sorted(shelters, key=lambda s: haversine_km(epicentre_lat, epicentre_lon, s["lat"], s["lon"]))
        
        if ranked_shelters:
            check_shelter_conditions(ranked_shelters[0]["name"])
            
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an AI civilian logistics coordinator. We have {displaced} displaced citizens needing shelter. "
                       "Distribute them across the provided shelters, prioritizing the nearest (first in list). Do not exceed a shelter's capacity. "
                       "You must output exactly one assignment object per shelter. Do not create multiple assignment objects for the same shelter. "
                       "For each shelter, calculate the total people assigned to it and provide a single assignment object with that aggregated count."),
            ("human", "Displaced Citizens: {displaced}\nShelters (Ordered by proximity): {shelters}")
        ])
        
        structured_llm = self.llm.with_structured_output(ShelterAssignmentList)
        chain = prompt | structured_llm
        
        try:
            result: ShelterAssignmentList = chain.invoke({
                "displaced": displaced_estimate,
                "shelters": ranked_shelters
            })
            
            assignments = result.assignments
            
            # Post-Process: Mutate the state accurately, prevent hallucination
            final_assignments = []
            
            while not memory_manager.acquire_lock("live_state_shelters", timeout=10):
                time.sleep(0.1)
                
            try:
                remaining = displaced_estimate
                total_housed = 0
                
                for s in ranked_shelters:
                    llm_assign = next((a for a in assignments if a.shelter_name == s["name"]), None)
                    if not llm_assign:
                        continue
                        
                    if remaining <= 0:
                        break
                        
                    take = min(remaining, llm_assign.people_assigned, s["capacity"])
                    
                    if take > 0:
                        s["capacity"] -= take
                        remaining -= take
                        total_housed += take
                        dist = haversine_km(epicentre_lat, epicentre_lon, s["lat"], s["lon"])
                        
                        final_assignments.append(ShelterAssignment(
                            shelter_name=s["name"],
                            people_assigned=take,
                            capacity_left=s["capacity"],
                            distance_km=round(dist, 2)
                        ))
            finally:
                memory_manager.release_lock("live_state_shelters")
                
            logger.info("shelter_allocation_success", total_housed=total_housed, unhoused=remaining)
            logger.metric("citizens_housed", float(total_housed), tags={"agent": "shelter_allocation"})
            if remaining > 0:
                logger.metric("citizens_unhoused_overflow", float(remaining), tags={"agent": "shelter_allocation"})
                
            return final_assignments
            
        except Exception as e:
            logger.error("shelter_allocation_failed_falling_back_to_legacy", error=str(e))
            return self._legacy_assign_shelters(damage_reports, shelters)
            
    def _legacy_assign_shelters(self, damage_reports: List[DamageReport], shelters: list) -> List[ShelterAssignment]:
        avg_damage_pct = sum(d.buildings_damaged_pct for d in damage_reports) / len(damage_reports)
        displaced_estimate = int(avg_damage_pct * 12) 

        epicentre_lat = sum(d.lat for d in damage_reports) / len(damage_reports)
        epicentre_lon = sum(d.lon for d in damage_reports) / len(damage_reports)

        ranked = sorted(shelters, key=lambda s: haversine_km(epicentre_lat, epicentre_lon, s["lat"], s["lon"]))

        assignments = []
        
        while not memory_manager.acquire_lock("live_state_shelters", timeout=10):
            time.sleep(0.1)
            
        try:
            remaining = displaced_estimate
            for s in ranked:
                if remaining <= 0:
                    break
                take = min(remaining, s["capacity"])
                if take > 0:
                    s["capacity"] -= take
                    remaining -= take
                    dist = haversine_km(epicentre_lat, epicentre_lon, s["lat"], s["lon"])
                    assignments.append(ShelterAssignment(
                        shelter_name=s["name"],
                        people_assigned=take,
                        capacity_left=s["capacity"],
                        distance_km=round(dist, 2)
                    ))
        finally:
            memory_manager.release_lock("live_state_shelters")
            
        return assignments

_agent = ShelterAllocationAgentV2()

def assign_shelters(damage_reports: List[DamageReport], shelters: list) -> List[ShelterAssignment]:
    return _agent.assign_shelters(damage_reports, shelters)
