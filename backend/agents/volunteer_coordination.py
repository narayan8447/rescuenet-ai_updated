"""
Agent 9 - Volunteer Coordination Agent (Production V2)

Purpose: Matches skilled volunteers (medical, engineer, driver) to outstanding 
tasks implied by the current disaster response using LLM semantic matching.
Mutates the shared `volunteers` state.
"""
import os
import time
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential
from backend.core.llm_pool import get_openrouter_llm, parse_llm_json
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from backend.models.schemas import PriorityItem, VolunteerAssignment
from backend.core.logging import logger
from backend.utils import haversine_km
from backend.core.memory import memory_manager

class VolunteerAssignmentList(BaseModel):
    """Wrapper to force LLM to output a list of VolunteerAssignments."""
    assignments: List[VolunteerAssignment] = Field(description="List of volunteer skill-to-task assignments.")

# Simulated Tool
def check_volunteer_safety_status(volunteer_name: str) -> dict:
    """Mock tool to simulate checking if a civilian volunteer has acknowledged safety waivers."""
    logger.info("tool_execution", tool="check_volunteer_safety_status", volunteer=volunteer_name)
    return {"waiver_signed": True, "gear_issued": False}

class VolunteerCoordinationAgentV2:
    def __init__(self):
        self.llm = get_openrouter_llm()
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def assign_volunteers(self, priorities: List[PriorityItem], volunteers: list, top_n: int = 3) -> List[VolunteerAssignment]:
        logger.info("volunteer_coordination_started", num_priorities=len(priorities), num_volunteers=len(volunteers))
        logger.metric("agent_start", 1.0, tags={"agent": "volunteer_coordination"})
        
        targets = priorities[:top_n]
        available_vols = [v for v in volunteers if v.get("available", False)]
        
        if not targets or not available_vols:
            logger.warn("no_targets_or_volunteers_available")
            return []
            
        if os.environ.get("OPENROUTER_API_KEY", "dummy_key") == "dummy_key":
            logger.warn("using_fallback_volunteer_coordination_due_to_missing_groq_key")
            return self._legacy_assign_volunteers(priorities, volunteers, top_n)
            
        # Simulate tool usage
        if available_vols:
            check_volunteer_safety_status(available_vols[0]["name"])
            
        targets_json = [t.model_dump() for t in targets]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a volunteer dispatch coordinator. Assign available civilian volunteers to the priority targets based on semantic skill matching. For example, 'hospital' needs 'medical', 'residential' needs 'engineer' or 'medical', 'warehouse' needs 'driver'. Prioritize closer volunteers to targets. A volunteer can only be assigned to one target. Provide a descriptive assigned_task.\n\n"
                       "You MUST respond with ONLY a valid JSON object (no markdown, no explanation, no function calls). Use this exact schema:\n"
                       '{{"assignments": [{{"volunteer_id": "string", "volunteer_name": "string", "assigned_to": "string", "assigned_task": "string"}}]}}'),
            ("human", "Priority Targets: {targets}\nAvailable Volunteers: {volunteers}")
        ])
        
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "targets": targets_json,
                "volunteers": available_vols
            })
            result = parse_llm_json(response.content, VolunteerAssignmentList)
            
            assignments = result.assignments
            
            final_assignments = []
            
            while not memory_manager.acquire_lock("live_state_volunteers", timeout=10):
                time.sleep(0.1)
                
            try:
                # Post-Process: Validate and securely mutate the state
                for llm_assign in assignments:
                    # Find the volunteer in the global state
                    vol = next((v for v in volunteers if v["name"] == llm_assign.volunteer_name and v.get("available", False)), None)
                    # Find the target
                    target = next((t for t in targets if t.entity in llm_assign.assigned_task or t.entity_type in llm_assign.assigned_task), None)
                    
                    # If target is ambiguous from assigned_task, we just assume the first target for distance calc fallback, 
                    # but let's try to match by name or distance.
                    # To be robust, let's just find the closest target to the volunteer if target not explicitly matched
                    if vol:
                        if not target:
                            target = min(targets, key=lambda t: haversine_km(vol["lat"], vol["lon"], t.lat, t.lon))
                            
                        # Lock volunteer
                        vol["available"] = False
                        dist = haversine_km(vol["lat"], vol["lon"], target.lat, target.lon)
                        
                        final_assignments.append(VolunteerAssignment(
                            volunteer_name=vol["name"],
                            skill=vol["skill"],
                            assigned_task=llm_assign.assigned_task,
                            distance_km=round(dist, 2)
                        ))
            finally:
                memory_manager.release_lock("live_state_volunteers")
                        
            logger.info("volunteer_coordination_success", assigned=len(final_assignments))
            if final_assignments:
                logger.metric("volunteers_activated", float(len(final_assignments)), tags={"agent": "volunteer_coordination"})
                
            return final_assignments
            
        except Exception as e:
            logger.error("volunteer_coordination_failed_falling_back_to_legacy", error=str(e))
            return self._legacy_assign_volunteers(priorities, volunteers)
            
    def _legacy_assign_volunteers(self, priorities: List[PriorityItem], volunteers: list, top_n: int = 3) -> List[VolunteerAssignment]:
        TASK_SKILL_MAP = {
            "hospital": "medical",
            "school": "medical",
            "residential": "engineer",
            "warehouse": "driver",
        }
        assignments = []
        
        while not memory_manager.acquire_lock("live_state_volunteers", timeout=10):
            time.sleep(0.1)
            
        try:
            for target in priorities[:top_n]:
                needed_skill = TASK_SKILL_MAP.get(target.entity_type, "medical")
                pool = [v for v in volunteers if v.get("available", False) and v["skill"] == needed_skill]
                if not pool:
                    pool = [v for v in volunteers if v.get("available", False)]
                if not pool:
                    continue
                nearest = min(pool, key=lambda v: haversine_km(v["lat"], v["lon"], target.lat, target.lon))
                dist = haversine_km(nearest["lat"], nearest["lon"], target.lat, target.lon)
                nearest["available"] = False
    
                assignments.append(
                    VolunteerAssignment(
                        volunteer_name=nearest["name"],
                        skill=nearest["skill"],
                        assigned_task=f"Support response at {target.entity}",
                        distance_km=round(dist, 2),
                    )
                )
        finally:
            memory_manager.release_lock("live_state_volunteers")
            
        return assignments

_agent = VolunteerCoordinationAgentV2()

def assign_volunteers(priorities: List[PriorityItem], volunteers: list, top_n: int = 3) -> List[VolunteerAssignment]:
    return _agent.assign_volunteers(priorities, volunteers, top_n)
