"""
Agent 4 - Resource Allocation Agent (Production V2)

Purpose: Assigns available resources to the highest-priority locations.
Uses Groq LLM for strategy and allocation optimization, supported by tools.
"""
import os
import time
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from backend.models.schemas import PriorityItem, ResourceAssignment
from backend.core.logging import logger
from backend.utils import haversine_km
from backend.core.memory import memory_manager

class ResourceAssignmentList(BaseModel):
    """Wrapper to force LLM to output a list of ResourceAssignments."""
    assignments: List[ResourceAssignment] = Field(description="List of optimized resource assignments.")

# Simulated Tool
def calculate_eta(resource_type: str, distance_km: float) -> float:
    """Mock tool to estimate ETA for a given resource type and distance."""
    logger.info("tool_execution", tool="calculate_eta", type=resource_type, dist=distance_km)
    speed = {"boat": 25, "ambulance": 40, "fire_truck": 35, "helicopter": 180}.get(resource_type, 30)
    return round((distance_km / speed) * 60, 1)

class ResourceAllocationAgentV2:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.environ.get("GROQ_API_KEY", "dummy_key"),
            max_retries=2
        )
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def allocate(self, disaster_type: str, priorities: List[PriorityItem], resources: dict, top_n: int = 4) -> List[ResourceAssignment]:
        logger.info("resource_allocation_started", disaster_type=disaster_type, num_priorities=len(priorities))
        logger.metric("agent_start", 1.0, tags={"agent": "resource_allocation"})
        
        targets = priorities[:top_n]
        if not targets:
            return []
            
        if os.environ.get("GROQ_API_KEY", "dummy_key") == "dummy_key":
            logger.warn("using_fallback_resource_allocation_due_to_missing_groq_key")
            return self._legacy_allocate(disaster_type, priorities, resources, top_n)
            
        # Simulate tool usage (pre-calculating speeds or checking fleet API)
        calculate_eta("ambulance", 10.0)
        
        # Prepare context data
        targets_json = [t.model_dump() for t in targets]
        # Only send available resources to LLM to save tokens
        available_resources = {
            rtype: [r for r in rlist if r["available"]]
            for rtype, rlist in resources.items()
        }
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an AI logistics dispatcher. Given a disaster type, a list of priority targets, and available fleet resources, map the most appropriate resource types to the targets. A flood needs boats/ambulances, an earthquake needs fire_trucks/ambulances/helicopters. Assign the nearest resource of the required type to each priority. Output a JSON list of ResourceAssignments."),
            ("human", "Disaster: {disaster}\nTargets: {targets}\nAvailable Fleet: {fleet}")
        ])
        
        structured_llm = self.llm.with_structured_output(ResourceAssignmentList)
        chain = prompt | structured_llm
        
        try:
            result: ResourceAssignmentList = chain.invoke({
                "disaster": disaster_type,
                "targets": targets_json,
                "fleet": available_resources
            })
            
            assignments = result.assignments
            
            while not memory_manager.acquire_lock("live_state_resources", timeout=10):
                time.sleep(0.1)
                
            try:
                # Post-Process: The LLM might hallucinate distances or ETAs, and we MUST mutate the real state dict
                # to mark resources as unavailable for subsequent calls.
                for assignment in assignments:
                    # Find the actual resource in our state tree
                    pool = resources.get(assignment.resource_type, [])
                    assigned_res = next((r for r in pool if r["id"] == assignment.resource_id), None)
                    target_entity = next((t for t in targets if t.entity == assignment.assigned_to), None)
                    
                    if assigned_res and target_entity:
                        assigned_res["available"] = False
                        # Correct math hallucinations
                        dist = haversine_km(assigned_res["lat"], assigned_res["lon"], target_entity.lat, target_entity.lon)
                        assignment.distance_km = round(dist, 2)
                        assignment.eta_minutes = calculate_eta(assignment.resource_type, dist)
            finally:
                memory_manager.release_lock("live_state_resources")
                        
            logger.info("resource_allocation_success", assigned=len(assignments))
            if assignments:
                logger.metric("resources_dispatched", float(len(assignments)), tags={"agent": "resource_allocation"})
                
            return assignments
            
        except Exception as e:
            logger.error("resource_allocation_failed_falling_back_to_legacy", error=str(e))
            return self._legacy_allocate(disaster_type, priorities, resources, top_n)
            
    def _legacy_allocate(self, disaster_type: str, priorities: List[PriorityItem], resources: dict, top_n: int = 4) -> List[ResourceAssignment]:
        DISASTER_RESOURCE_NEEDS = {
            "flood": ["boat", "ambulance"],
            "earthquake": ["fire_truck", "ambulance", "helicopter"],
            "cyclone": ["fire_truck", "boat", "ambulance"],
            "fire": ["fire_truck", "ambulance"],
            "landslide": ["fire_truck", "helicopter", "ambulance"],
            "building_collapse": ["fire_truck", "ambulance", "helicopter"],
        }
        
        targets = priorities[:top_n]
        assignments = []
        
        while not memory_manager.acquire_lock("live_state_resources", timeout=10):
            time.sleep(0.1)
            
        try:
            for target in targets:
                # Basic fallback mapping
                req_type = "ambulance"
                if target.entity_type == "residential":
                    req_type = "fire_truck"
                elif target.entity_type == "warehouse":
                    req_type = "helicopter"
    
                pool = [r for r in resources.get(req_type, []) if r.get("available", False)]
                if not pool:
                    continue
    
                # naive nearest neighbor
                nearest = min(pool, key=lambda r: haversine_km(r["lat"], r["lon"], target.lat, target.lon))
                nearest["available"] = False
                dist = haversine_km(nearest["lat"], nearest["lon"], target.lat, target.lon)
    
                assignments.append(
                    ResourceAssignment(
                        resource_id=nearest["id"],
                        resource_type=req_type,
                        assigned_to=target.entity,
                        distance_km=round(dist, 2),
                        eta_minutes=calculate_eta(req_type, dist)
                    )
                )
        finally:
            memory_manager.release_lock("live_state_resources")
            
        return assignments

_agent = ResourceAllocationAgentV2()

def allocate(disaster_type: str, priorities: List[PriorityItem], resources: dict, top_n: int = 4) -> List[ResourceAssignment]:
    return _agent.allocate(disaster_type, priorities, resources, top_n)
