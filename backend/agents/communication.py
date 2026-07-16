"""
Agent 10 - Communication Agent

Purpose: generate public alert messages across channels (SMS, WhatsApp,
Emergency Alert) and languages (English, Hindi), pointing people to their
assigned shelter. A production system would fan these out via an SMS
gateway/WhatsApp Business API; here we generate the message content.
"""
from typing import List
from backend.models.schemas import DisasterEvent, ShelterAssignment, Alert

TEMPLATES_EN = "{disaster} Warning for {location}. Move to {shelter} within {minutes} minutes. Avoid blocked roads and follow rescue team instructions."
TEMPLATES_HI = "{location} mein {disaster} ki chetavani. Kripya {minutes} minute ke andar {shelter} jaayen. Band sadakon se bachen aur rescue team ke nirdeshon ka paalan karen."


def generate_alerts(event: DisasterEvent, shelter_assignments: List[ShelterAssignment]) -> List[Alert]:
    if not shelter_assignments:
        primary_shelter = "the nearest designated shelter"
    else:
        primary_shelter = shelter_assignments[0].shelter_name

    minutes = 45  # simulated evacuation window; would be derived from route ETA + disaster spread rate

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
