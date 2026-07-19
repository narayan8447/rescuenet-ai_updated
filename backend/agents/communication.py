"""
Agent 10 - Communication Agent (Production V2)

Purpose: Generates highly targeted public alert messages across channels 
(SMS, WhatsApp, Emergency Alert) and languages (English, Hindi).
Uses Groq LLM for tone formatting and translation.
"""
import os
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential
from backend.core.llm_pool import get_openrouter_llm, parse_llm_json
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from backend.models.schemas import DisasterEvent, ShelterAssignment, Alert
from backend.core.logging import logger

class AlertList(BaseModel):
    """Wrapper to force LLM to output a list of Alerts."""
    alerts: List[Alert] = Field(description="List of multilingual public alerts.")

# Simulated Tool
def dispatch_sms_gateway(message: str) -> dict:
    """Mock tool to simulate dispatching to a Twilio/SMS gateway."""
    logger.info("tool_execution", tool="dispatch_sms_gateway", length=len(message))
    return {"status": "queued", "gateway": "twilio"}

class CommunicationAgentV2:
    def __init__(self):
        self.llm = get_openrouter_llm()
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_alerts(self, event: DisasterEvent, shelter_assignments: List[ShelterAssignment]) -> List[Alert]:
        logger.info("communication_started", event_type=event.disaster_type)
        logger.metric("agent_start", 1.0, tags={"agent": "communication"})
        
        if os.environ.get("OPENROUTER_API_KEY", "dummy_key") == "dummy_key":
            logger.warn("using_fallback_communication_due_to_missing_groq_key")
            return self._legacy_generate_alerts(event, shelter_assignments)
            
        primary_shelter = "the nearest designated shelter"
        if shelter_assignments:
            primary_shelter = shelter_assignments[0].shelter_name
            
        minutes = 45 # Simulated evacuation window
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an official government emergency spokesperson. Draft concise, authoritative evacuation alerts for the given disaster. Provide alerts in both English and Hindi. Channels should be 'SMS', 'WhatsApp', and 'Emergency Alert'. SMS must be under 160 characters. Tell the public to move to the specified shelter within the time limit and avoid blocked roads. Ensure translation accuracy. Return exactly 6 alerts (2 languages * 3 channels).\n\n"
                       "You MUST respond with ONLY a valid JSON object (no markdown, no explanation, no function calls). Use this exact schema:\n"
                       '{{"alerts": [{{"language": "string", "channel": "string", "message": "string"}}]}}'),
            ("human", "Disaster: {disaster} in {location}\nPrimary Shelter: {shelter}\nEvacuate within: {minutes} minutes")
        ])
        
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "disaster": event.disaster_type.replace("_", " ").title(),
                "location": event.location_name,
                "shelter": primary_shelter,
                "minutes": minutes
            })
            result = parse_llm_json(response.content, AlertList)
            
            alerts = result.alerts
            
            # Simulate dispatch tool
            if alerts:
                dispatch_sms_gateway(alerts[0].message)
                
            logger.info("communication_success", num_alerts=len(alerts))
            logger.metric("alerts_drafted", float(len(alerts)), tags={"agent": "communication"})
                
            return alerts
            
        except Exception as e:
            logger.error("communication_failed", error=str(e))
            raise e
            
    def _legacy_generate_alerts(self, event: DisasterEvent, shelter_assignments: List[ShelterAssignment]) -> List[Alert]:
        if not shelter_assignments:
            primary_shelter = "the nearest designated shelter"
        else:
            primary_shelter = shelter_assignments[0].shelter_name

        minutes = 45  
        
        TEMPLATES_EN = "{disaster} Warning for {location}. Move to {shelter} within {minutes} minutes. Avoid blocked roads and follow rescue team instructions."
        TEMPLATES_HI = "{location} mein {disaster} ki chetavani. Kripya {minutes} minute ke andar {shelter} jaayen. Band sadakon se bachen aur rescue team ke nirdeshon ka paalan karen."

        alerts = []
        for lang, template in (("English", TEMPLATES_EN), ("Hindi", TEMPLATES_HI)):
            msg = template.format(
                disaster=event.disaster_type.replace("_", " ").title(),
                location=event.location_name,
                shelter=primary_shelter,
                minutes=minutes,
            )
            for channel in ("SMS", "WhatsApp", "Emergency Alert"):
                alerts.append(Alert(language=lang, channel=channel, message=msg))
        return alerts

_agent = CommunicationAgentV2()

def generate_alerts(event: DisasterEvent, shelter_assignments: List[ShelterAssignment]) -> List[Alert]:
    return _agent.generate_alerts(event, shelter_assignments)
