"""
Agent 5 - Route Optimization Agent (Production V2)

Purpose: Evaluates resource assignments against damage reports and priority
locations to calculate optimal routing, applying penalties for blocked roads.
Uses Groq LLM for routing strategy and dynamic hazard avoidance.
"""
import os
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from backend.models.schemas import ResourceAssignment, DamageReport, RouteInfo, PriorityItem
from backend.core.logging import logger
from backend.utils import haversine_km

class RouteInfoList(BaseModel):
    """Wrapper to force LLM to output a list of RouteInfos."""
    routes: List[RouteInfo] = Field(description="Optimized routing plan for dispatched resources.")

# Simulated Tool
def fetch_live_traffic(destination: str) -> dict:
    """Mock tool to simulate fetching live traffic and road closure APIs (e.g. Waze/Google Maps)."""
    logger.info("tool_execution", tool="fetch_live_traffic", destination=destination)
    return {"congestion_level": "moderate", "active_closures": False}

class RouteOptimizationAgentV2:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=os.environ.get("GROQ_API_KEY", "dummy_key"),
            max_retries=2
        )
        
    def _road_status_for(self, target_name: str, priorities: List[PriorityItem], damage_reports: List[DamageReport]) -> str:
        poi = next((p for p in priorities if p.entity == target_name), None)
        if not poi:
            return "open"
        nearest = min(damage_reports, key=lambda d: haversine_km(poi.lat, poi.lon, d.lat, d.lon))
        return nearest.road_status
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def plan_routes(self, assignments: List[ResourceAssignment], priorities: List[PriorityItem], damage_reports: List[DamageReport]) -> List[RouteInfo]:
        logger.info("route_optimization_started", num_assignments=len(assignments))
        logger.metric("agent_start", 1.0, tags={"agent": "route_optimization"})
        
        if not assignments:
            return []
            
        if os.environ.get("GROQ_API_KEY", "dummy_key") == "dummy_key":
            logger.warn("using_fallback_route_optimization_due_to_missing_groq_key")
            return self._legacy_plan_routes(assignments, priorities, damage_reports)
            
        # Simulate tool usage for the first destination to demonstrate tool integration
        fetch_live_traffic(assignments[0].assigned_to)
        
        # We need to give the LLM the local road statuses so it can reason about routes
        assignment_context = []
        for a in assignments:
            road_status = self._road_status_for(a.assigned_to, priorities, damage_reports)
            assignment_context.append({
                "resource_id": a.resource_id,
                "destination": a.assigned_to,
                "base_distance_km": a.distance_km,
                "road_status": road_status
            })
            
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an emergency routing AI. For each resource assignment, determine the route status based on the destination's road_status. If road_status is 'blocked', set status='rerouted' and increase distance by ~40% (penalty=1.4). If 'partially_blocked', set status='delayed' and increase distance by ~15% (penalty=1.15). If 'open', status='clear' and penalty=1.0. Provide a descriptive note. Output a list matching the exact number of assignments."),
            ("human", "Assignments and Road Context: {context}")
        ])
        
        structured_llm = self.llm.with_structured_output(RouteInfoList)
        chain = prompt | structured_llm
        
        try:
            result: RouteInfoList = chain.invoke({"context": assignment_context})
            
            # Post-Process: Validate and align the outputs with original assignments to prevent hallucinated IDs
            final_routes = []
            for original_assign in assignments:
                # Find matching route from LLM output
                llm_route = next((r for r in result.routes if r.resource_id == original_assign.resource_id), None)
                if not llm_route:
                    # If LLM missed one, fallback
                    logger.warn("llm_missed_route_generating_fallback", resource_id=original_assign.resource_id)
                    road_status = self._road_status_for(original_assign.assigned_to, priorities, damage_reports)
                    penalty = 1.4 if road_status == "blocked" else 1.15 if road_status == "partially_blocked" else 1.0
                    llm_route = RouteInfo(
                        resource_id=original_assign.resource_id,
                        destination=original_assign.assigned_to,
                        distance_km=round(original_assign.distance_km * penalty, 2),
                        status="rerouted" if road_status == "blocked" else "delayed" if road_status == "partially_blocked" else "clear",
                        note="Fallback route generation applied."
                    )
                else:
                    # Sanity check distance logic
                    expected_min_dist = original_assign.distance_km
                    if llm_route.distance_km < expected_min_dist:
                        llm_route.distance_km = expected_min_dist # Cannot be shorter than straight line
                        
                final_routes.append(llm_route)
                
            # Metrics: Track how many routes are blocked/delayed
            rerouted_count = sum(1 for r in final_routes if r.status != "clear")
            logger.metric("routes_rerouted", float(rerouted_count), tags={"agent": "route_optimization"})
            logger.info("route_optimization_success", num_routes=len(final_routes))
            
            return final_routes
            
        except Exception as e:
            logger.error("route_optimization_failed", error=str(e))
            raise e
            
    def _legacy_plan_routes(self, assignments: List[ResourceAssignment], priorities: List[PriorityItem], damage_reports: List[DamageReport]) -> List[RouteInfo]:
        routes = []
        for a in assignments:
            road_status = self._road_status_for(a.assigned_to, priorities, damage_reports)

            if road_status == "blocked":
                status, note, penalty = "rerouted", "Direct road blocked - alternate route added ~40% distance", 1.4
            elif road_status == "partially_blocked":
                status, note, penalty = "delayed", "Partial obstruction - proceeding with caution, +15% time", 1.15
            else:
                status, note, penalty = "clear", "Direct route, no obstructions detected", 1.0

            routes.append(
                RouteInfo(
                    resource_id=a.resource_id,
                    destination=a.assigned_to,
                    distance_km=round(a.distance_km * penalty, 2),
                    status=status,
                    note=note,
                )
            )
        return routes

_agent = RouteOptimizationAgentV2()

def plan_routes(assignments: List[ResourceAssignment], priorities: List[PriorityItem], damage_reports: List[DamageReport]) -> List[RouteInfo]:
    return _agent.plan_routes(assignments, priorities, damage_reports)
