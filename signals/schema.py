# orion/signals/schema.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class SignalV12:
    # identity
    event_id: Optional[str]
    asset: str
    symbol: str

    # scores
    score_norm: Optional[float]
    adj_score: Optional[float]

    # explanation
    why_path: Optional[str]
    when_months: Optional[float]

    # market confirmation + risks
    confirmation_features: Dict[str, Any]
    risk_flags: Dict[str, Any]

    # transparency
    market_status: str
    reason: str

    # metadata
    timestamp: str  # ISO (UTC)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def iso_now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()