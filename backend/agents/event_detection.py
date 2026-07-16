"""
Agent 1 - Event Detection Agent

Purpose: confirm that a disaster has occurred and structure the raw report
into a DisasterEvent. In production this fuses emergency calls, social
media/NLP classification, satellite imagery, and CCTV/drone feeds (Whisper,
YOLO, Vision Transformers). Here we validate/normalize the citizen-reported
trigger and attach a simulated confidence score.
"""
from datetime import datetime, timezone
from backend.models.schemas import DisasterTriggerRequest, DisasterEvent
from backend.utils import seeded_random

VALID_TYPES = {"flood", "earthquake", "cyclone", "fire", "landslide", "building_collapse"}


def detect(req: DisasterTriggerRequest) -> DisasterEvent:
    dtype = req.disaster_type.strip().lower().replace(" ", "_")
    if dtype not in VALID_TYPES:
        dtype = "flood"  # sensible fallback rather than failing the pipeline

    rng = seeded_random(f"{dtype}-{req.location_name}-{req.lat}-{req.lon}")
    # Multiple independent sources agreeing raises confidence; we simulate
    # this by sampling a high-confidence band since the user actively
    # reported it (vs. ambient sensor noise).
    confidence = round(rng.uniform(0.90, 0.99), 3)

    return DisasterEvent(
        disaster_type=dtype,
        location_name=req.location_name,
        lat=req.lat,
        lon=req.lon,
        confidence=confidence,
        detected_at=datetime.now(timezone.utc).isoformat(),
    )
