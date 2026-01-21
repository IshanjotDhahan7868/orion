"""
Event classification logic.

Classify raw news items into structured events with types,
confidence scores, and associated graph nodes.
"""

EVENT_RULES = {
    "capex_expansion": [
        "invest", "investment", "capex", "expand", "build",
        "new plant", "factory", "fab"
    ],
    "supply_constraint": [
        "shortage", "halted", "shutdown", "disrupted",
        "sanctions", "restricted"
    ],
    "demand_surge": [
        "surging demand", "record orders", "backlog",
        "orders doubled", "strong demand"
    ],
    "regulatory": [
        "ban", "approval", "regulation", "policy",
        "subsidy", "tariff"
    ],
    "geopolitical_conflict": [
        "attack", "war", "missile", "invasion",
        "military strike"
    ]
}


def classify_event(text: str) -> str | None:
    """
    Return the dominant event type or None if no signal exists.
    """
    text_lower = text.lower()
    scores = {}

    for event_type, keywords in EVENT_RULES.items():
        scores[event_type] = sum(
            1 for kw in keywords if kw in text_lower
        )

    best_event = max(scores, key=scores.get)
    return best_event if scores[best_event] > 0 else None


def score_confidence(
    event_type: str | None,
    entities: dict
) -> int:
    """
    Confidence score from 1–10.
    """
    if event_type is None:
        return 0

    score = 0

    if entities.get("companies"):
        score += 3
    if entities.get("commodities") or entities.get("technologies"):
        score += 2
    if event_type:
        score += 3
    if len(entities.get("countries", [])) > 1:
        score += 2

    return min(score, 10)
