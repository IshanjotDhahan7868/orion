# orion/signals/exporter.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml

from orion.signals.schema import SignalV12, iso_now_utc


BASE_DIR = Path(__file__).resolve().parents[1]  # .../orion/
CFG_DIR = BASE_DIR / "config"
PROCESSED_DIR = BASE_DIR / "data" / "processed"


def _get(row: pd.Series, col: str, default=None):
    return row[col] if col in row.index and pd.notna(row[col]) else default


def _float(row: pd.Series, col: str) -> Optional[float]:
    v = _get(row, col, None)
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _risk_flags(asset: str, why_path: str, assets_meta: dict) -> Dict[str, Any]:
    meta = assets_meta.get(asset, {}) if isinstance(assets_meta, dict) else {}
    asset_type = str(meta.get("type", "equity")).lower()

    flags = {
        "type": asset_type,
        "crowding_etf": (asset_type == "etf"),
        "regulatory": False,
        "cyclical": False,
        "notes": [],
    }

    wp = why_path or ""
    if any(k in wp for k in ["Trade_Restrictions"]):
        flags["regulatory"] = True
        flags["notes"].append("Policy/export controls could affect trajectory.")
    if any(k in wp for k in ["Oil_and_Gas", "Industrial_Construction", "Transportation_Infrastructure"]):
        flags["cyclical"] = True
        flags["notes"].append("Cyclical sensitivity may increase drawdowns.")
    if flags["crowding_etf"]:
        flags["notes"].append("ETF exposure may be crowded.")

    return flags


def build_signal(row: pd.Series, assets_meta: dict) -> SignalV12:
    event_id = _get(row, "event_id", _get(row, "source_event_id", None))
    asset = str(_get(row, "asset", "UNKNOWN"))

    symbol = str(_get(row, "symbol", asset))
    market_status = str(_get(row, "market_status", "ok"))
    reason = str(_get(row, "reason", ""))

    score_norm = _float(row, "score_norm")
    adj_score = _float(row, "adj_score")

    why_path = _get(row, "why_path", _get(row, "best_path", None))
    when_months = _float(row, "when_months")

    # confirmation features (match your Week 6 columns)
    confirmation_features: Dict[str, Any] = {
        "rs_1m": _float(row, "rs_1m"),
        "rs_3m": _float(row, "rs_3m"),
        "above_ma50": _get(row, "above_ma50", None),
        "above_ma200": _get(row, "above_ma200", None),
        "golden": _get(row, "golden", None),
        "vol_z20": _float(row, "vol_z20"),
        # optional if present:
        "confirm_score": _float(row, "confirm_score"),
        "confirm_rs1m": _float(row, "confirm_rs1m"),
        "confirm_rs3m": _float(row, "confirm_rs3m"),
        "confirm_trend": _float(row, "confirm_trend"),
        "confirm_vol": _float(row, "confirm_vol"),
    }

    risk_flags = _risk_flags(asset=asset, why_path=str(why_path or ""), assets_meta=assets_meta)

    return SignalV12(
        event_id=event_id,
        asset=asset,
        symbol=symbol,
        score_norm=score_norm,
        adj_score=adj_score,
        why_path=why_path,
        when_months=when_months,
        confirmation_features=confirmation_features,
        risk_flags=risk_flags,
        market_status=market_status,
        reason=reason,
        timestamp=iso_now_utc(),
    )


def render_card(sig: SignalV12) -> str:
    score = sig.adj_score if sig.adj_score is not None else sig.score_norm
    score_s = f"{score:.3f}" if score is not None else "N/A"

    path = sig.why_path or "(no path available)"
    when = sig.when_months

    # market sentence
    if sig.market_status in ("skipped", "missing"):
        market_line = f"Market check: **not confirmed** ({sig.market_status}: {sig.reason})."
    else:
        m = sig.confirmation_features
        trend_ok = (m.get("above_ma50") == 1 and m.get("golden") == 1)
        bits = []
        if m.get("rs_1m") is not None:
            bits.append(f"RS 1m={m.get('rs_1m'):.2f}")
        if m.get("rs_3m") is not None:
            bits.append(f"RS 3m={m.get('rs_3m'):.2f}")
        bits.append("trend=OK" if trend_ok else "trend=weak")
        if m.get("vol_z20") is not None:
            bits.append(f"vol_z20={m.get('vol_z20'):.2f}")
        market_line = "Market check: " + ", ".join(bits) + "."

    # risk line
    notes = sig.risk_flags.get("notes", [])
    risk_line = "Risks: " + ("; ".join(notes) if notes else "none flagged (v0).")

    p1 = (
        f"**{sig.asset} ({sig.symbol})** scored **{score_s}** on this ORION run. "
        f"Causal trail: `{path}`."
    )
    if when is not None:
        p1 += f" Expected impact window: **~{when:.1f} months**."

    return p1 + "\n\n" + market_line + "\n\n" + risk_line


def export(
    signals_week6_csv: Path = PROCESSED_DIR / "signals_week6.csv",
    out_json: Path = PROCESSED_DIR / "signals_v1_2.json",
    out_md: Path = PROCESSED_DIR / "weekly_brief.md",
    top_n: int = 10,
) -> None:
    if not signals_week6_csv.exists():
        raise FileNotFoundError(f"Missing {signals_week6_csv}. Run Week 6 first.")

    df = pd.read_csv(signals_week6_csv)

    sort_col = "adj_score" if "adj_score" in df.columns else "score_norm"
    if sort_col in df.columns:
        df = df.sort_values(sort_col, ascending=False)

    assets_meta = _load_yaml(CFG_DIR / "assets.yaml")

    signals: List[SignalV12] = [build_signal(r, assets_meta=assets_meta) for _, r in df.iterrows()]

    out_json.write_text(json.dumps([s.to_dict() for s in signals], indent=2), encoding="utf-8")

    lines: List[str] = []
    lines.append("# ORION Weekly Signals\n")
    lines.append(f"- Generated: {iso_now_utc()}")
    lines.append(f"- Source: `{signals_week6_csv.as_posix()}`\n")
    lines.append(f"## Top {min(top_n, len(signals))}\n")

    for i, sig in enumerate(signals[:top_n], start=1):
        lines.append(f"### {i}. {sig.asset} ({sig.symbol})")
        lines.append(render_card(sig))
        lines.append("")

    out_md.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    export()
    print("Wrote signals_v1_2.json and weekly_brief.md")
