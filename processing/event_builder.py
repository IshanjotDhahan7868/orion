"""
Event builder.

Combine extracted entities, classification, confidence,
and lag into a single canonical event object.
"""

from datetime import datetime
from uuid import uuid4

from .event_classifier import classify_event, score_confidence
from .lag_estimator import estimate_lag


def build_event(
    headline: str,
    raw_text: str,
    published_at: str,
    source: str,
    entities: dict
) -> dict | None:
    event_type = classify_event(raw_text)
    confidence = score_confidence(event_type, entities)

    if confidence < 5:
        return None

    return {
        "event_id": str(uuid4()),
        "headline": headline,
        "source": source,
        "published_at": published_at,
        "event_type": event_type,
        "confidence": confidence,
        "entities": entities,
        "lag": estimate_lag(event_type),
        "raw_text": raw_text,
        "created_at": datetime.utcnow().isoformat()
    }
