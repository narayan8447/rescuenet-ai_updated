"""
Agent 12 - Prediction Agent

Purpose: forecast how the situation evolves over the next few hours (flood/
fire spread, hospital demand) so the orchestrator can pre-position
resources. Production version would use LSTM/XGBoost/Graph Neural Networks
over historical + live sensor data; here we use a simple, clearly-labelled
extrapolation so the *pipeline shape* is correct and swappable later.
"""
from typing import List
from backend.models.schemas import DisasterEvent, DamageReport, Forecast

SPREAD_RATE = {  # % increase in affected-area severity per hour, illustrative
    "flood": 0.08,
    "fire": 0.15,
    "cyclone": 0.05,
    "earthquake": 0.02,   # aftershock risk more than "spread"
    "landslide": 0.04,
    "building_collapse": 0.01,
}


def forecast(event: DisasterEvent, damage_reports: List[DamageReport]) -> List[Forecast]:
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
