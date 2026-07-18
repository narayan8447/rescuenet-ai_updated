"""
Agent 12 - Prediction Agent (Production V2)

Purpose: Forecasts how the situation evolves over the next few hours
(e.g., flood/fire spread, hospital demand). Uses an LLM with external
simulated tools (like weather) to make grounded predictions.
"""
import os
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential
from backend.core.llm_pool import get_groq_llm
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from backend.models.schemas import DisasterEvent, DamageReport, Forecast
from backend.core.logging import logger

class ForecastList(BaseModel):
    """Wrapper to force LLM to output a list of Forecasts."""
    forecasts: List[Forecast] = Field(description="List of predicted metrics for the disaster over time.")

from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

@tool
def fetch_weather_forecast(location: str) -> str:
    """Fetches the 24-hour weather forecast for a given location. Always use this before predicting."""
    logger.info("tool_execution", tool="fetch_weather_forecast", location=location)
    return '{"wind_speed_kmh": 35, "precipitation_mm": 120, "condition": "worsening"}'

class PredictionAgentV2:
    def __init__(self):
        self.llm = get_groq_llm()
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def forecast(self, event: DisasterEvent, damage_reports: List[DamageReport]) -> List[Forecast]:
        logger.info("prediction_started", event_type=event.disaster_type)
        logger.metric("agent_start", 1.0, tags={"agent": "prediction"})
        
        if not damage_reports:
            return []
            
        if os.environ.get("GROQ_API_KEY", "dummy_key") == "dummy_key":
            logger.warn("using_fallback_prediction_due_to_missing_groq_key")
            return self._legacy_forecast(event, damage_reports)
            
        avg_severity = sum(d.severity_score for d in damage_reports) / len(damage_reports)
        total_casualties = sum(d.estimated_casualties for d in damage_reports)
        
        messages = [
            SystemMessage(content="You are a disaster modeling AI. Use tools to gather data, then predict severity at 6, 12, and 24 hours."),
            HumanMessage(content=f"Disaster: {event.disaster_type}. Location: {event.location_name}. Severity: {avg_severity}. Casualties: {total_casualties}.")
        ]
        
        # Step 1: Bind tool and invoke to get tool call
        llm_with_tools = self.llm.bind_tools([fetch_weather_forecast])
        response_msg = llm_with_tools.invoke(messages)
        messages.append(response_msg)
        
        # Step 2: Execute tool if requested
        if response_msg.tool_calls:
            for tool_call in response_msg.tool_calls:
                if tool_call["name"] == "fetch_weather_forecast":
                    tool_res = fetch_weather_forecast.invoke(tool_call["args"])
                    messages.append(ToolMessage(content=tool_res, tool_call_id=tool_call["id"]))
                    
        # Step 3: Force structured output based on the full conversation history
        structured_llm = self.llm.with_structured_output(ForecastList)
        try:
            result = structured_llm.invoke(messages)
            forecasts = result.forecasts
            
            logger.info("prediction_success", num_forecasts=len(forecasts))
            for f in forecasts:
                logger.metric(f"forecast_{f.metric}_{f.horizon_hours}h", float(f.predicted_value), tags={"agent": "prediction"})
                
            return forecasts
            
        except Exception as e:
            logger.error("prediction_failed", error=str(e))
            raise e
            
    def _legacy_forecast(self, event: DisasterEvent, damage_reports: List[DamageReport]) -> List[Forecast]:
        SPREAD_RATE = {
            "flood": 0.08,
            "fire": 0.15,
            "cyclone": 0.05,
            "earthquake": 0.02,
            "landslide": 0.04,
            "building_collapse": 0.01,
        }
        rate = SPREAD_RATE.get(event.disaster_type, 0.05)
        avg_severity = sum(d.severity_score for d in damage_reports) / len(damage_reports)
        total_casualties = sum(d.estimated_casualties for d in damage_reports)

        forecasts = []
        for h in (6, 12, 24):
            projected_severity = min(100.0, round(avg_severity * (1 + rate * (h / 6)), 1))
            forecasts.append(
                Forecast(
                    horizon_hours=h,
                    metric=f"{event.disaster_type}_severity_index",
                    predicted_value=projected_severity,
                    note="Simulated extrapolation - replace with LSTM/XGBoost trained on historical sensor data for production use.",
                )
            )

        projected_demand = int(total_casualties * (1 + rate) * 0.4)
        forecasts.append(
            Forecast(
                horizon_hours=24,
                metric="hospital_admission_demand",
                predicted_value=float(projected_demand),
                note="Projected additional hospital admissions over next 24h based on current casualty trend.",
            )
        )
        return forecasts

_agent = PredictionAgentV2()

def forecast(event: DisasterEvent, damage_reports: List[DamageReport]) -> List[Forecast]:
    return _agent.forecast(event, damage_reports)
