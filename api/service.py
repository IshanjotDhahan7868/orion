from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
from datetime import UTC, date, datetime

import pandas as pd
import yaml

from db.store import (
    create_alert_destination,
    ensure_initialized,
    generate_brief_prompt,
    generate_brief_with_ollama,
    get_customer_account,
    list_alert_destinations,
    list_briefs,
    latest_brief,
    latest_portfolio_snapshot,
    list_watchlists,
    load_cached_events,
    load_cached_signals,
    mark_alert_sent,
    refresh_market_intelligence,
    save_brief,
    save_portfolio_snapshot,
    seed_ontology_from_config,
    seed_watchlists_from_config,
    upsert_customer_account,
    upsert_watchlist,
)
from execution.position_sizing import build_capped_weights
from graph.asset_impact import aggregate_assets
from graph.dependency_graph import DependencyGraph
from graph.propagate import propagate_impact
from processing.entity_extraction import extract_entities
from processing.event_builder import build_event
from signals.delivery import deliver_signal_alert


BASE_DIR = Path(__file__).resolve().parents[1]
CFG_DIR = BASE_DIR / "config"
PROCESSED_DIR = BASE_DIR / "data" / "processed"


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _signal_notes_to_flags(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(item) for item in raw]
    if isinstance(raw, dict):
        notes = raw.get("notes")
        if isinstance(notes, list) and notes:
            return [str(item) for item in notes]
        flags = [key for key, value in raw.items() if isinstance(value, bool) and value]
        return flags
    return []


def _normalize_signal_row(row: dict[str, Any], idx: int) -> dict[str, Any]:
    adjusted_score = row.get("adj_score", row.get("adjusted_score", row.get("score_norm", 0.0)))
    market_status = str(row.get("market_status", "ok"))
    notes = _signal_notes_to_flags(row.get("risk_flags", []))
    return {
        "id": idx + 1,
        "event_id": str(row.get("event_id", "")),
        "asset": str(row.get("asset", "")),
        "rank": int(row.get("rank", idx + 1)),
        "score_raw": float(row.get("score_raw", row.get("score_norm", adjusted_score) or 0.0)),
        "score_norm": float(row.get("score_norm", adjusted_score) or 0.0),
        "why_path": str(row.get("why_path", "")),
        "when_months": float(row.get("when_months", 0) or 0),
        "confirmed": market_status == "ok",
        "risk_flags_json": json.dumps(notes),
        "adjusted_score": float(adjusted_score or 0.0),
        "graph_version": str(row.get("graph_version", "v1.1")),
        "created_at": str(row.get("timestamp", row.get("created_at", row.get("batch_id", "")))),
        "headline": row.get("headline"),
        "event_type": row.get("event_type"),
    }


def _load_signals_rows() -> list[dict[str, Any]]:
    json_path = PROCESSED_DIR / "signals_v1_2.json"
    csv_path = PROCESSED_DIR / "signals_week6.csv"

    if json_path.exists():
        payload = _read_json(json_path)
        if isinstance(payload, dict) and "signals" in payload:
            rows = payload["signals"]
        else:
            rows = payload
        if isinstance(rows, list):
            return [r for r in rows if isinstance(r, dict)]

    if csv_path.exists():
        df = pd.read_csv(csv_path)
        return df.fillna("").to_dict(orient="records")

    return []


def list_signals(limit: int = 50) -> list[dict[str, Any]]:
    ensure_initialized()
    rows = load_cached_signals(limit=limit)
    if rows:
        return rows[:limit]

    rows = _load_signals_rows()
    normalized = [_normalize_signal_row(row, idx) for idx, row in enumerate(rows)]
    normalized.sort(key=lambda row: row["adjusted_score"], reverse=True)
    return normalized[:limit]


def _asset_to_theme_map() -> dict[str, str]:
    asset_map = _load_yaml(CFG_DIR / "assets.yaml")
    graph = DependencyGraph.from_yaml(str(CFG_DIR / "graph.yaml"))
    out: dict[str, str] = {}

    for asset, meta in asset_map.items():
        nodes = meta.get("nodes", []) or []
        if not nodes:
            out[asset] = "UNMAPPED"
            continue

        first_node = nodes[0]
        node_meta = graph.node_meta.get(first_node, {})
        out[asset] = str(node_meta.get("theme", "UNMAPPED"))

    return out


def _normalize_event_row(row: dict[str, Any], idx: int) -> dict[str, Any]:
    seeded_nodes = row.get("seeded_nodes") or row.get("affected_nodes") or row.get("nodes") or []
    if isinstance(seeded_nodes, str):
        try:
            seeded_nodes = json.loads(seeded_nodes)
        except Exception:
            seeded_nodes = [part.strip() for part in seeded_nodes.split("|") if part.strip()]

    rationale = row.get("headline") or row.get("summary") or row.get("raw_text") or ""
    return {
        "id": idx + 1,
        "event_type": str(row.get("event_type", "unknown")),
        "seeded_nodes_json": json.dumps(seeded_nodes),
        "confidence": float(row.get("confidence", 0) or 0),
        "rationale": str(rationale),
        "parser_source": str(row.get("source", row.get("parser_source", "orion-engine"))),
        "created_at": str(row.get("created_at", row.get("published_at", ""))),
        "headline": row.get("headline"),
    }


def list_recent_events(limit: int = 20) -> list[dict[str, Any]]:
    ensure_initialized()
    cached = load_cached_events(limit=limit)
    if cached:
        return cached[:limit]

    events: list[dict[str, Any]] = []
    candidates = [
        PROCESSED_DIR / "events.jsonl",
        PROCESSED_DIR / "events.json",
        PROCESSED_DIR / "events.yaml",
        PROCESSED_DIR / "events.yml",
        PROCESSED_DIR / "events.csv",
    ]

    for path in candidates:
        if not path.exists():
            continue

        if path.suffix == ".jsonl":
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
            break

        if path.suffix == ".json":
            payload = _read_json(path)
            if isinstance(payload, list):
                events = [row for row in payload if isinstance(row, dict)]
            elif isinstance(payload, dict):
                events = [payload]
            break

        if path.suffix in (".yaml", ".yml"):
            payload = _load_yaml(path)
            if isinstance(payload, list):
                events = [row for row in payload if isinstance(row, dict)]
            elif isinstance(payload, dict):
                events = [payload]
            break

        if path.suffix == ".csv":
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                events = list(reader)
            break

    normalized = [_normalize_event_row(row, idx) for idx, row in enumerate(events)]
    normalized.sort(key=lambda row: row["created_at"], reverse=True)
    return normalized[:limit]


def get_graph_node(node_id: str) -> dict[str, Any] | None:
    graph = DependencyGraph.from_yaml(str(CFG_DIR / "graph.yaml"))
    meta = graph.node_meta.get(node_id)
    if not meta:
        return None
    return {
        "id": meta["id"],
        "theme": meta.get("theme"),
        "type": meta.get("type"),
        "description": meta.get("what_is_this"),
        "what_affects_it": meta.get("what_affects_it", []),
        "assets": meta.get("assets", {}),
    }


def _map_event_to_nodes(event: dict[str, Any], company_map: dict, tech_map: dict) -> list[str]:
    entities = event.get("entities", {}) or {}
    companies = entities.get("companies", []) or []
    technologies = entities.get("technologies", []) or []

    injected_nodes: set[str] = set()
    for company in companies:
        if company in company_map:
            injected_nodes.update(company_map[company].get("nodes", []) or [])
    for technology in technologies:
        if technology in tech_map:
            injected_nodes.update(tech_map[technology].get("nodes", []) or [])
    return sorted(injected_nodes)


def run_what_if(text: str, dry_run: bool = True, top_n: int = 10) -> dict[str, Any]:
    graph = DependencyGraph.from_yaml(str(CFG_DIR / "graph.yaml"))
    asset_map = _load_yaml(CFG_DIR / "assets.yaml")
    company_map = _load_yaml(CFG_DIR / "companies.yaml")
    tech_map = _load_yaml(CFG_DIR / "technologies.yaml")

    entities = extract_entities(text)
    event = build_event(
        headline=text[:120],
        raw_text=text,
        published_at="dry-run",
        source="api",
        entities=entities,
    )

    if event is None:
        return {
            "message": "No actionable event was detected from that text.",
            "events": [],
            "signals": [],
        }

    seeded_nodes = _map_event_to_nodes(event, company_map=company_map, tech_map=tech_map)
    if not seeded_nodes:
        return {
            "message": "The event was classified, but no graph nodes were matched from the extracted entities.",
            "events": [
                {
                    **event,
                    "seeded_nodes": [],
                }
            ],
            "signals": [],
        }

    node_impacts, best_node_paths = propagate_impact(graph, seeded_nodes)
    asset_scores, asset_meta = aggregate_assets(node_impacts, asset_map, best_node_paths)
    ranked = sorted(asset_scores.items(), key=lambda item: item[1], reverse=True)[:top_n]
    top_score = ranked[0][1] if ranked else 1.0

    signals = []
    for rank, (asset, score) in enumerate(ranked, start=1):
        meta = asset_meta.get(asset) or {}
        path = meta.get("path", [])
        signals.append(
            {
                "asset": asset,
                "score": round(float(score), 6),
                "score_norm": round(float(score / top_score), 6) if top_score else 0.0,
                "rank": rank,
                "path": path,
                "why_path": " -> ".join(path),
                "lag_months": int(meta.get("lag_months", 0) or 0),
            }
        )

    message = (
        f"ORION seeded {len(seeded_nodes)} graph nodes and found {len(signals)} impacted assets."
        if dry_run
        else f"ORION processed the event and found {len(signals)} impacted assets."
    )

    return {
        "message": message,
        "events": [
            {
                **event,
                "seeded_nodes": seeded_nodes,
            }
        ],
        "signals": signals,
    }


def build_portfolio_recommendation(
    limit: int = 12,
    min_score: float = 0.0,
    gross_exposure: float = 1.0,
    max_per_asset: float = 0.10,
    max_per_theme: float = 0.30,
    confirmed_only: bool = True,
) -> dict[str, Any]:
    signals = list_signals(limit=100)
    filtered = [
        signal
        for signal in signals
        if signal["adjusted_score"] >= min_score and (signal["confirmed"] or not confirmed_only)
    ]
    filtered = filtered[: max(1, limit)]

    if not filtered:
        return {
            "positions": [],
            "summary": {
                "count": 0,
                "gross_exposure": 0.0,
                "average_score": 0.0,
                "confirmed_only": confirmed_only,
            },
        }

    score_map = {signal["asset"]: float(signal["adjusted_score"]) for signal in filtered}
    asset_to_theme = _asset_to_theme_map()
    weights = build_capped_weights(
        score_map,
        asset_to_theme=asset_to_theme,
        max_per_asset=max_per_asset,
        max_per_theme=max_per_theme,
        gross_exposure=gross_exposure,
    )

    positions = []
    for signal in filtered:
        weight = weights.get(signal["asset"], 0.0)
        if weight <= 0:
            continue
        positions.append(
            {
                "asset": signal["asset"],
                "weight": round(weight, 6),
                "theme": asset_to_theme.get(signal["asset"], "UNMAPPED"),
                "score": signal["adjusted_score"],
                "why_path": signal["why_path"],
                "lag_months": signal["when_months"],
                "confirmed": signal["confirmed"],
                "event_type": signal.get("event_type"),
            }
        )

    positions.sort(key=lambda position: position["weight"], reverse=True)
    avg_score = sum(position["score"] for position in positions) / len(positions)
    theme_exposure: dict[str, float] = {}
    for position in positions:
        theme = position["theme"]
        theme_exposure[theme] = theme_exposure.get(theme, 0.0) + position["weight"]

    return {
        "positions": positions,
        "summary": {
            "count": len(positions),
            "gross_exposure": round(sum(position["weight"] for position in positions), 6),
            "average_score": round(avg_score, 6),
            "confirmed_only": confirmed_only,
            "theme_exposure": {k: round(v, 6) for k, v in sorted(theme_exposure.items())},
            "constraints": {
                "max_per_asset": max_per_asset,
                "max_per_theme": max_per_theme,
                "gross_exposure": gross_exposure,
                "min_score": min_score,
            },
        },
    }


def refresh_intelligence_state() -> dict[str, Any]:
    signals = list_signals(limit=200)
    events = list_recent_events(limit=100)
    sync_counts = refresh_market_intelligence(signals=signals, events=events)
    ontology_counts = seed_ontology_from_config()
    watchlist_count = seed_watchlists_from_config()
    if not watchlist_count and not list_watchlists():
        upsert_watchlist("core", ["NVDA", "TSM", "ASML", "LRCX", "AMAT", "MSFT", "GOOGL", "COPPER"])
    return {
        "signals": sync_counts["signals"],
        "events": sync_counts["events"],
        "ontology_entities": ontology_counts["entities"],
        "ontology_relationships": ontology_counts["relationships"],
        "watchlists": len(list_watchlists()),
    }


def get_watchlists() -> list[dict[str, Any]]:
    return list_watchlists()


def set_watchlist(name: str, assets: list[str], notes: str = "") -> dict[str, Any]:
    return upsert_watchlist(name=name, assets=assets, notes=notes)


def create_portfolio_snapshot(
    label: str = "Current ORION Portfolio",
    limit: int = 12,
    min_score: float = 0.0,
    gross_exposure: float = 1.0,
    max_per_asset: float = 0.10,
    max_per_theme: float = 0.30,
    confirmed_only: bool = True,
) -> dict[str, Any]:
    recommendation = build_portfolio_recommendation(
        limit=limit,
        min_score=min_score,
        gross_exposure=gross_exposure,
        max_per_asset=max_per_asset,
        max_per_theme=max_per_theme,
        confirmed_only=confirmed_only,
    )
    return save_portfolio_snapshot(label=label, recommendation=recommendation)


def get_latest_portfolio_snapshot() -> dict[str, Any] | None:
    return latest_portfolio_snapshot()


def generate_daily_brief(
    watchlist_name: str = "core",
    use_ai: bool = True,
) -> dict[str, Any]:
    signals = list_signals(limit=12)
    events = list_recent_events(limit=10)
    watchlists = {watchlist["name"]: watchlist for watchlist in list_watchlists()}
    watchlist = watchlists.get(watchlist_name) or next(iter(watchlists.values()), None)
    portfolio = latest_portfolio_snapshot()
    if portfolio is None:
        portfolio = create_portfolio_snapshot()

    prompt = generate_brief_prompt(signals=signals, events=events, watchlist=watchlist, portfolio=portfolio)
    ai_body = generate_brief_with_ollama(prompt) if use_ai else None
    body = ai_body
    title = f"ORION Daily Brief - {date.today().isoformat()}"

    if not body:
        top_assets = ", ".join(signal["asset"] for signal in signals[:5]) or "no major signals"
        watch_assets = ", ".join((watchlist or {}).get("assets", [])[:6]) or "no watchlist assets"
        top_positions = ", ".join(
            f"{position['asset']} {position['weight']:.1%}" for position in portfolio.get("positions", [])[:5]
        )
        body = (
            "1. Regime\n"
            f"ORION is currently centered on the highest-conviction themes implied by {top_assets}.\n\n"
            "2. What matters now\n"
            f"Recent events and market-confirmed signals indicate the most actionable paths remain concentrated in the current signal set.\n\n"
            "3. Watchlist focus\n"
            f"Key names to monitor: {watch_assets}.\n\n"
            "4. Portfolio actions\n"
            f"Current suggested positioning: {top_positions or 'no active positions generated yet'}."
        )

    metadata = {
        "watchlist_name": (watchlist or {}).get("name"),
        "signal_count": len(signals),
        "event_count": len(events),
        "portfolio_snapshot_id": portfolio.get("snapshot_id"),
        "used_ai": bool(ai_body),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    return save_brief(brief_date=date.today().isoformat(), title=title, body=body, metadata=metadata)


def get_latest_brief() -> dict[str, Any] | None:
    return latest_brief()


def get_or_create_account_profile(
    clerk_user_id: str,
    email: str | None = None,
    full_name: str | None = None,
) -> dict[str, Any]:
    existing = get_customer_account(clerk_user_id)
    if existing is not None:
        return existing
    return upsert_customer_account(
        clerk_user_id=clerk_user_id,
        email=email,
        full_name=full_name,
        buyer_type="hedge_fund",
        subscription_status="inactive",
        plan_key="free",
    )


def update_account_profile(
    clerk_user_id: str,
    email: str | None = None,
    full_name: str | None = None,
    buyer_type: str | None = None,
    organization_name: str | None = None,
    onboarding_notes: str | None = None,
) -> dict[str, Any]:
    return upsert_customer_account(
        clerk_user_id=clerk_user_id,
        email=email,
        full_name=full_name,
        buyer_type=buyer_type,
        organization_name=organization_name,
        onboarding_notes=onboarding_notes,
    )


def update_account_billing(
    clerk_user_id: str,
    *,
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
    stripe_price_id: str | None = None,
    stripe_product_name: str | None = None,
    subscription_status: str | None = None,
    plan_key: str | None = None,
) -> dict[str, Any]:
    return upsert_customer_account(
        clerk_user_id=clerk_user_id,
        stripe_customer_id=stripe_customer_id,
        stripe_subscription_id=stripe_subscription_id,
        stripe_price_id=stripe_price_id,
        stripe_product_name=stripe_product_name,
        subscription_status=subscription_status,
        plan_key=plan_key,
    )


def list_account_alerts(clerk_user_id: str) -> list[dict[str, Any]]:
    return list_alert_destinations(clerk_user_id)


def create_account_alert(
    clerk_user_id: str,
    label: str,
    channel: str,
    destination: str,
    min_score: float = 0.7,
    confirmed_only: bool = True,
) -> dict[str, Any]:
    profile = get_or_create_account_profile(clerk_user_id)
    return create_alert_destination(
        clerk_user_id=clerk_user_id,
        label=label,
        channel=channel,
        destination=destination,
        min_score=min_score,
        confirmed_only=confirmed_only,
        buyer_type=profile.get("buyer_type"),
        active=True,
    )


def build_alert_payload(clerk_user_id: str, alert_id: int | None = None) -> dict[str, Any]:
    profile = get_or_create_account_profile(clerk_user_id)
    alerts = list_alert_destinations(clerk_user_id)
    if not alerts:
        return {
            "profile": profile,
            "alerts": [],
            "deliveries": [],
            "message": "No alert destinations configured.",
        }

    if alert_id is not None:
        alerts = [alert for alert in alerts if alert["alert_id"] == alert_id]
        if not alerts:
            return {
                "profile": profile,
                "alerts": [],
                "deliveries": [],
                "message": f"Alert {alert_id} not found for this account.",
            }

    signals = list_signals(limit=25)
    deliveries = []
    for alert in alerts:
        selected = [
            signal
            for signal in signals
            if signal["adjusted_score"] >= alert["min_score"]
            and (signal["confirmed"] or not alert["confirmed_only"])
        ][:5]
        if not selected:
            deliveries.append(
                {
                    "alert_id": alert["alert_id"],
                    "label": alert["label"],
                    "ok": False,
                    "reason": "No signals matched the alert filters.",
                }
            )
            continue

        lines = [
            f"{signal['asset']} score={signal['adjusted_score']:.2f} lag={signal['when_months']}mo path={signal['why_path']}"
            for signal in selected
        ]
        subject = f"ORION alert: {alert['label']}"
        body = (
            f"Buyer type: {profile.get('buyer_type', 'hedge_fund')}\n"
            f"Plan: {profile.get('plan_key', 'free')}\n\n"
            "Top matching signals:\n"
            + "\n".join(f"- {line}" for line in lines)
        )
        delivery = deliver_signal_alert(
            channel=alert["channel"],
            destination=alert["destination"],
            subject=subject,
            body=body,
            metadata={
                "clerk_user_id": clerk_user_id,
                "alert_id": alert["alert_id"],
                "buyer_type": profile.get("buyer_type"),
            },
        )
        if delivery.get("ok"):
            mark_alert_sent(alert["alert_id"])
        deliveries.append(
            {
                "alert_id": alert["alert_id"],
                "label": alert["label"],
                "channel": alert["channel"],
                "destination": alert["destination"],
                "signals": selected,
                **delivery,
            }
        )

    return {
        "profile": profile,
        "alerts": alerts,
        "deliveries": deliveries,
        "message": f"Prepared {len(deliveries)} alert delivery attempt(s).",
    }


def get_performance_summary() -> dict[str, Any]:
    signals = list_signals(limit=200)
    events = list_recent_events(limit=100)
    briefs = list_briefs(limit=12)
    portfolio = latest_portfolio_snapshot()

    total_signals = len(signals)
    confirmed_signals = [signal for signal in signals if signal["confirmed"]]
    avg_score = (
        round(sum(float(signal["adjusted_score"]) for signal in signals) / total_signals, 4)
        if total_signals
        else 0.0
    )
    confirmed_rate = round(len(confirmed_signals) / total_signals, 4) if total_signals else 0.0
    avg_lag = (
        round(sum(float(signal["when_months"]) for signal in signals) / total_signals, 2)
        if total_signals
        else 0.0
    )

    theme_exposure: dict[str, float] = {}
    event_type_counts: dict[str, int] = {}
    for signal in signals:
        for node in [part.strip() for part in str(signal["why_path"]).replace("->", "→").split("→") if part.strip()]:
            event_type_counts[node] = event_type_counts.get(node, 0) + 1
    if portfolio:
        theme_exposure = {
            key: float(value)
            for key, value in (portfolio.get("summary", {}).get("theme_exposure") or {}).items()
        }

    top_assets = [
        {
            "asset": signal["asset"],
            "score": float(signal["adjusted_score"]),
            "confirmed": bool(signal["confirmed"]),
            "lag_months": float(signal["when_months"]),
            "event_type": signal.get("event_type"),
            "why_path": signal["why_path"],
            "created_at": signal["created_at"],
        }
        for signal in signals[:20]
    ]

    recent_briefs = [
        {
            "brief_id": brief["brief_id"],
            "brief_date": brief["brief_date"],
            "title": brief["title"],
            "created_at": brief["created_at"],
        }
        for brief in briefs
    ]

    proof_points = [
        {
            "label": "Market-confirmed hit rate",
            "value": confirmed_rate,
            "display": f"{confirmed_rate * 100:.1f}%",
            "description": "Share of current signals passing market confirmation filters.",
        },
        {
            "label": "Average signal strength",
            "value": avg_score,
            "display": f"{avg_score:.2f}",
            "description": "Average adjusted score across the latest signal set.",
        },
        {
            "label": "Average lag to thesis horizon",
            "value": avg_lag,
            "display": f"{avg_lag:.1f} mo",
            "description": "Average modeled time horizon across current signals.",
        },
        {
            "label": "Saved briefs",
            "value": len(briefs),
            "display": str(len(briefs)),
            "description": "Analyst brief archive available for replay and customer review.",
        },
    ]

    return {
        "metrics": {
            "total_signals": total_signals,
            "confirmed_signals": len(confirmed_signals),
            "confirmed_rate": confirmed_rate,
            "average_score": avg_score,
            "average_lag_months": avg_lag,
            "events_tracked": len(events),
            "briefs_saved": len(briefs),
        },
        "proof_points": proof_points,
        "theme_exposure": theme_exposure,
        "signal_history": top_assets,
        "recent_briefs": recent_briefs,
        "event_nodes": sorted(
            [{"name": name, "count": count} for name, count in event_type_counts.items()],
            key=lambda item: item["count"],
            reverse=True,
        )[:12],
        "portfolio": portfolio,
    }
