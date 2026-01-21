"""
Lag estimation logic.

Estimate how long it takes for an event to impact markets.
"""

LAG_RULES = {
    "capex_expansion": 24,
    "supply_constraint": 1,
    "geopolitical_conflict": 0,
    "regulatory": 6,
    "demand_surge": 3
}


def estimate_lag(event_type: str | None) -> dict | None:
    if event_type is None:
        return None

    months = LAG_RULES.get(event_type, 6)

    return {
        "type": "immediate" if months == 0 else
                "short" if months <= 3 else
                "long",
        "estimate_months": months
    }
