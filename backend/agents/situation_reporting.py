"""
Agent 11 - Situation Reporting Agent (Production V2)
Purpose: Compiles every other agent's output into one cohesive, human-readable 
markdown narrative summary for government dashboards and media briefings. 
Natively integrates the Agentic RAG engine to ground the report in official SOPs and web facts.
"""

import os
from typing import List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from backend.core.llm_pool import get_openrouter_llm
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from backend.models.schemas import (
    DisasterEvent, DamageReport, PriorityItem, ResourceAssignment, RouteInfo,
    HospitalAssignment, ShelterAssignment, ReliefPlan, VolunteerAssignment,
    Forecast
)
from backend.core.logging import logger
from backend.rag.rag_engine import rag_engine
from backend.rag.models import RAGQuery

class NarrativeSummary(BaseModel):
    """Wrapper to force LLM to output a single string."""
    summary: Optional[str] = Field(default="No summary generated.", description="Markdown formatted executive summary of the disaster response.")

class SituationReportingAgentV2:
    def __init__(self):
        self.llm = get_openrouter_llm()
             
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def compile_summary(
        self,
        event: DisasterEvent,
        damage_reports: List[DamageReport],
        priorities: List[PriorityItem],
        resource_assignments: List[ResourceAssignment],
        routes: List[RouteInfo],
        hospital_assignments: List[HospitalAssignment],
        shelter_assignments: List[ShelterAssignment],
        relief_plan: List[ReliefPlan],
        volunteer_assignments: List[VolunteerAssignment],
        forecasts: List[Forecast],
    ) -> str:
        logger.info("situation_reporting_started")
        logger.metric("agent_start", 1.0, tags={"agent": "situation_reporting"})
        
        if os.environ.get("OPENROUTER_API_KEY", "dummy_key") == "dummy_key":
            logger.warn("using_fallback_situation_reporting_due_to_missing_groq_key")
            return self._legacy_compile_summary(event, damage_reports, priorities, resource_assignments, routes, hospital_assignments, shelter_assignments, relief_plan, volunteer_assignments, forecasts)
        
        # 1. Fetch live external context / SOPs using our new Agentic RAG
        rag_query_str = f"Standard Operating Procedures for handling a {event.disaster_type} emergency in {event.location_name}"
        logger.info("situation_reporting_rag_lookup", query=rag_query_str)
        
        rag_payload = RAGQuery(query=rag_query_str, disaster_type=event.disaster_type, top_k=3)
        rag_response = rag_engine.retrieve(rag_payload)
        external_context = rag_response.answer

        # 2. Gather internal state statistics
        total_casualties = sum(d.estimated_casualties for d in damage_reports)
        total_displaced = sum(s.people_assigned for s in shelter_assignments)
        top_priority = priorities[0].entity if priorities else "N/A"
        rerouted = sum(1 for r in routes if r.status != "clear")
        
        context_data = {
            "disaster": event.disaster_type.replace('_', ' ').title(),
            "location": event.location_name,
            "casualties": total_casualties,
            "displaced": total_displaced,
            "top_priority": top_priority,
            "resources_dispatched": len(resource_assignments),
            "routes_delayed": rerouted,
            "hospitals_utilized": len(hospital_assignments),
            "shelters_utilized": len(shelter_assignments),
            "volunteers_active": len(volunteer_assignments),
            "rag_and_web_intelligence": external_context
        }
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are the Chief of Operations drafting an Executive Situation Report. "
                       "Synthesize the internal emergency metrics alongside the provided 'RAG and Web Intelligence' notes. "
                       "Draft a cohesive, highly dense Markdown summary using clean bullet points. "
                       "You MUST explicitly call out casualty metrics and contrast internal logistics with the external guidelines/web context supplied."),
            ("human", "Current State Data: {state}")
        ])
        
        structured_llm = self.llm.with_structured_output(NarrativeSummary)
        chain = prompt | structured_llm
        
        try:
            result: NarrativeSummary = chain.invoke({"state": context_data})
            summary = result.summary
            
            logger.info("situation_reporting_success", length=len(summary))
            logger.metric("report_generated", 1.0, tags={"agent": "situation_reporting"})
            return summary
            
        except Exception as e:
            logger.error("situation_reporting_failed", error=str(e))
            raise e
            
    def _legacy_compile_summary(
        self,
        event: DisasterEvent,
        damage_reports: List[DamageReport],
        priorities: List[PriorityItem],
        resource_assignments: List[ResourceAssignment],
        routes: List[RouteInfo],
        hospital_assignments: List[HospitalAssignment],
        shelter_assignments: List[ShelterAssignment],
        relief_plan: List[ReliefPlan],
        volunteer_assignments: List[VolunteerAssignment],
        forecasts: List[Forecast],
    ) -> str:
        total_casualties = sum(d.estimated_casualties for d in damage_reports)
        total_displaced = sum(s.people_assigned for s in shelter_assignments)
        top_priority = priorities[0].entity if priorities else "N/A"
        rerouted = sum(1 for r in routes if r.status != "clear")
        lines = [
            f"{event.disaster_type.replace('_', ' ').title()} detected in {event.location_name} "
            f"(confidence {event.confidence * 100:.1f}%).",
            f"{len(damage_reports)} affected zones identified, with an estimated {total_casualties} casualties requiring assistance.",
            f"Highest-priority response target: {top_priority}.",
            f"{len(resource_assignments)} emergency resources dispatched; {rerouted} of {len(routes)} routes required rerouting or delay due to road conditions.",
            f"{sum(h.patients_assigned for h in hospital_assignments)} patients assigned across {len(hospital_assignments)} hospitals.",
            f"{total_displaced} people assigned to shelters across {len(shelter_assignments)} sites; relief supplies calculated for all active shelters.",
            f"{len(volunteer_assignments)} volunteers activated to support field teams.",
        ]
        if forecasts:
            demand_forecast = next((f for f in forecasts if f.metric == "hospital_admission_demand"), None)
            if demand_forecast:
                lines.append(
                    f"Forecast: an additional ~{int(demand_forecast.predicted_value)} hospital admissions expected within 24 hours if conditions continue."
                )
        return " ".join(lines)

_agent = SituationReportingAgentV2()

def compile_summary(
    event: DisasterEvent,
    damage_reports: List[DamageReport],
    priorities: List[PriorityItem],
    resource_assignments: List[ResourceAssignment],
    routes: List[RouteInfo],
    hospital_assignments: List[HospitalAssignment],
    shelter_assignments: List[ShelterAssignment],
    relief_plan: List[ReliefPlan],
    volunteer_assignments: List[VolunteerAssignment],
    forecasts: List[Forecast],
) -> str:
    return _agent.compile_summary(
        event, damage_reports, priorities, resource_assignments, routes, 
        hospital_assignments, shelter_assignments, relief_plan, volunteer_assignments, forecasts
    )