from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

import yaml


BASE_DIR = Path(__file__).resolve().parents[1]
CFG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
DEFAULT_DB_PATH = DATA_DIR / "orion_state.db"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def get_db_path() -> Path:
    raw = os.getenv("ORION_STATE_DB")
    return Path(raw) if raw else DEFAULT_DB_PATH


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def ensure_initialized() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS ontology_entities (
                entity_id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                name TEXT NOT NULL,
                theme TEXT,
                attributes_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ontology_relationships (
                relationship_id TEXT PRIMARY KEY,
                from_entity_id TEXT NOT NULL,
                to_entity_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                attributes_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS signals_cache (
                signal_id INTEGER PRIMARY KEY,
                event_id TEXT,
                asset TEXT NOT NULL,
                rank_value INTEGER,
                score_raw REAL,
                score_norm REAL,
                why_path TEXT,
                when_months REAL,
                confirmed INTEGER NOT NULL,
                risk_flags_json TEXT NOT NULL,
                adjusted_score REAL,
                graph_version TEXT,
                created_at TEXT,
                headline TEXT,
                event_type TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events_cache (
                event_id INTEGER PRIMARY KEY,
                event_type TEXT NOT NULL,
                seeded_nodes_json TEXT NOT NULL,
                confidence REAL,
                rationale TEXT,
                parser_source TEXT,
                created_at TEXT,
                headline TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS watchlists (
                name TEXT PRIMARY KEY,
                assets_json TEXT NOT NULL,
                notes TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                summary_json TEXT NOT NULL,
                positions_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS analyst_briefs (
                brief_id INTEGER PRIMARY KEY AUTOINCREMENT,
                brief_date TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS customer_accounts (
                clerk_user_id TEXT PRIMARY KEY,
                email TEXT,
                full_name TEXT,
                buyer_type TEXT NOT NULL,
                organization_name TEXT,
                onboarding_notes TEXT,
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                stripe_price_id TEXT,
                stripe_product_name TEXT,
                subscription_status TEXT NOT NULL,
                plan_key TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS alert_destinations (
                alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                clerk_user_id TEXT NOT NULL,
                label TEXT NOT NULL,
                channel TEXT NOT NULL,
                destination TEXT NOT NULL,
                min_score REAL NOT NULL,
                confirmed_only INTEGER NOT NULL,
                buyer_type TEXT,
                active INTEGER NOT NULL,
                last_sent_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def seed_ontology_from_config() -> dict[str, int]:
    ensure_initialized()
    assets = _load_yaml(CFG_DIR / "assets.yaml")
    graph = _load_yaml(CFG_DIR / "graph.yaml")
    inserted_entities = 0
    inserted_relationships = 0
    now = utc_now()

    with connect() as conn:
        for node in graph.get("nodes", []):
            entity_id = f"node:{node['id']}"
            conn.execute(
                """
                INSERT INTO ontology_entities(entity_id, entity_type, name, theme, attributes_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_id) DO UPDATE SET
                    entity_type=excluded.entity_type,
                    name=excluded.name,
                    theme=excluded.theme,
                    attributes_json=excluded.attributes_json,
                    updated_at=excluded.updated_at
                """,
                (
                    entity_id,
                    "graph_node",
                    node["id"],
                    node.get("theme"),
                    json.dumps(node),
                    now,
                ),
            )
            inserted_entities += 1

        for asset, meta in assets.items():
            entity_id = f"asset:{asset}"
            conn.execute(
                """
                INSERT INTO ontology_entities(entity_id, entity_type, name, theme, attributes_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_id) DO UPDATE SET
                    entity_type=excluded.entity_type,
                    name=excluded.name,
                    theme=excluded.theme,
                    attributes_json=excluded.attributes_json,
                    updated_at=excluded.updated_at
                """,
                (
                    entity_id,
                    meta.get("type", "asset"),
                    asset,
                    None,
                    json.dumps(meta),
                    now,
                ),
            )
            inserted_entities += 1
            for node_id in meta.get("nodes", []) or []:
                rel_id = f"{entity_id}->node:{node_id}"
                conn.execute(
                    """
                    INSERT INTO ontology_relationships(relationship_id, from_entity_id, to_entity_id, relationship_type, attributes_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(relationship_id) DO UPDATE SET
                        attributes_json=excluded.attributes_json,
                        updated_at=excluded.updated_at
                    """,
                    (
                        rel_id,
                        entity_id,
                        f"node:{node_id}",
                        "exposed_to",
                        json.dumps({"source": "assets.yaml"}),
                        now,
                    ),
                )
                inserted_relationships += 1

        for idx, edge in enumerate(graph.get("edges", []), start=1):
            rel_id = f"edge:{idx}:{edge['from']}:{edge['to']}"
            conn.execute(
                """
                INSERT INTO ontology_relationships(relationship_id, from_entity_id, to_entity_id, relationship_type, attributes_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(relationship_id) DO UPDATE SET
                    attributes_json=excluded.attributes_json,
                    updated_at=excluded.updated_at
                """,
                (
                    rel_id,
                    f"node:{edge['from']}",
                    f"node:{edge['to']}",
                    "causal_edge",
                    json.dumps(edge),
                    now,
                ),
            )
            inserted_relationships += 1

    return {"entities": inserted_entities, "relationships": inserted_relationships}


def seed_watchlists_from_config() -> int:
    ensure_initialized()
    watchlists_cfg = _load_yaml(CFG_DIR / "watchlists.yaml")
    if not isinstance(watchlists_cfg, dict):
        return 0

    count = 0
    for name, meta in watchlists_cfg.items():
        if not isinstance(meta, dict):
            continue
        assets = meta.get("assets", []) or []
        notes = str(meta.get("notes", ""))
        upsert_watchlist(name=name, assets=assets, notes=notes)
        count += 1
    return count


def refresh_market_intelligence(signals: list[dict[str, Any]], events: list[dict[str, Any]]) -> dict[str, int]:
    ensure_initialized()
    now = utc_now()
    with connect() as conn:
        conn.execute("DELETE FROM signals_cache")
        conn.execute("DELETE FROM events_cache")

        for signal in signals:
            conn.execute(
                """
                INSERT INTO signals_cache(
                    signal_id, event_id, asset, rank_value, score_raw, score_norm, why_path, when_months,
                    confirmed, risk_flags_json, adjusted_score, graph_version, created_at, headline, event_type, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(signal.get("id", 0)),
                    signal.get("event_id"),
                    signal.get("asset"),
                    signal.get("rank"),
                    signal.get("score_raw"),
                    signal.get("score_norm"),
                    signal.get("why_path"),
                    signal.get("when_months"),
                    1 if signal.get("confirmed") else 0,
                    signal.get("risk_flags_json", "[]"),
                    signal.get("adjusted_score"),
                    signal.get("graph_version"),
                    signal.get("created_at"),
                    signal.get("headline"),
                    signal.get("event_type"),
                    now,
                ),
            )

        for event in events:
            conn.execute(
                """
                INSERT INTO events_cache(
                    event_id, event_type, seeded_nodes_json, confidence, rationale,
                    parser_source, created_at, headline, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(event.get("id", 0)),
                    event.get("event_type"),
                    event.get("seeded_nodes_json", "[]"),
                    event.get("confidence"),
                    event.get("rationale"),
                    event.get("parser_source"),
                    event.get("created_at"),
                    event.get("headline"),
                    now,
                ),
            )

    return {"signals": len(signals), "events": len(events)}


def load_cached_signals(limit: int = 50) -> list[dict[str, Any]]:
    ensure_initialized()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT signal_id AS id, event_id, asset, rank_value AS rank, score_raw, score_norm, why_path,
                   when_months, confirmed, risk_flags_json, adjusted_score, graph_version,
                   created_at, headline, event_type
            FROM signals_cache
            ORDER BY adjusted_score DESC, created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def load_cached_events(limit: int = 20) -> list[dict[str, Any]]:
    ensure_initialized()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT event_id AS id, event_type, seeded_nodes_json, confidence, rationale,
                   parser_source, created_at, headline
            FROM events_cache
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def upsert_watchlist(name: str, assets: list[str], notes: str = "") -> dict[str, Any]:
    ensure_initialized()
    now = utc_now()
    payload = json.dumps(sorted(dict.fromkeys([asset.strip().upper() for asset in assets if asset.strip()])))
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO watchlists(name, assets_json, notes, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                assets_json=excluded.assets_json,
                notes=excluded.notes,
                updated_at=excluded.updated_at
            """,
            (name, payload, notes, now),
        )
    return {"name": name, "assets": json.loads(payload), "notes": notes, "updated_at": now}


def list_watchlists() -> list[dict[str, Any]]:
    ensure_initialized()
    with connect() as conn:
        rows = conn.execute(
            "SELECT name, assets_json, notes, updated_at FROM watchlists ORDER BY updated_at DESC"
        ).fetchall()
    out = []
    for row in rows:
        out.append(
            {
                "name": row["name"],
                "assets": json.loads(row["assets_json"]),
                "notes": row["notes"] or "",
                "updated_at": row["updated_at"],
            }
        )
    return out


def save_portfolio_snapshot(label: str, recommendation: dict[str, Any]) -> dict[str, Any]:
    ensure_initialized()
    now = utc_now()
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO portfolio_snapshots(label, summary_json, positions_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                label,
                json.dumps(recommendation.get("summary", {})),
                json.dumps(recommendation.get("positions", [])),
                now,
            ),
        )
        snapshot_id = int(cur.lastrowid)
    return {
        "snapshot_id": snapshot_id,
        "label": label,
        "summary": recommendation.get("summary", {}),
        "positions": recommendation.get("positions", []),
        "created_at": now,
    }


def latest_portfolio_snapshot() -> dict[str, Any] | None:
    ensure_initialized()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT snapshot_id, label, summary_json, positions_json, created_at
            FROM portfolio_snapshots
            ORDER BY created_at DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return {
        "snapshot_id": row["snapshot_id"],
        "label": row["label"],
        "summary": json.loads(row["summary_json"]),
        "positions": json.loads(row["positions_json"]),
        "created_at": row["created_at"],
    }


def save_brief(brief_date: str, title: str, body: str, metadata: dict[str, Any]) -> dict[str, Any]:
    ensure_initialized()
    now = utc_now()
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO analyst_briefs(brief_date, title, body, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (brief_date, title, body, json.dumps(metadata), now),
        )
        brief_id = int(cur.lastrowid)
    return {
        "brief_id": brief_id,
        "brief_date": brief_date,
        "title": title,
        "body": body,
        "metadata": metadata,
        "created_at": now,
    }


def latest_brief() -> dict[str, Any] | None:
    ensure_initialized()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT brief_id, brief_date, title, body, metadata_json, created_at
            FROM analyst_briefs
            ORDER BY created_at DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return {
        "brief_id": row["brief_id"],
        "brief_date": row["brief_date"],
        "title": row["title"],
        "body": row["body"],
        "metadata": json.loads(row["metadata_json"]),
        "created_at": row["created_at"],
    }


def list_briefs(limit: int = 10) -> list[dict[str, Any]]:
    ensure_initialized()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT brief_id, brief_date, title, body, metadata_json, created_at
            FROM analyst_briefs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        {
            "brief_id": row["brief_id"],
            "brief_date": row["brief_date"],
            "title": row["title"],
            "body": row["body"],
            "metadata": json.loads(row["metadata_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def get_customer_account(clerk_user_id: str) -> dict[str, Any] | None:
    ensure_initialized()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT clerk_user_id, email, full_name, buyer_type, organization_name,
                   onboarding_notes, stripe_customer_id, stripe_subscription_id,
                   stripe_price_id, stripe_product_name, subscription_status, plan_key,
                   created_at, updated_at
            FROM customer_accounts
            WHERE clerk_user_id = ?
            """,
            (clerk_user_id,),
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def upsert_customer_account(
    clerk_user_id: str,
    email: str | None = None,
    full_name: str | None = None,
    buyer_type: str | None = None,
    organization_name: str | None = None,
    onboarding_notes: str | None = None,
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
    stripe_price_id: str | None = None,
    stripe_product_name: str | None = None,
    subscription_status: str | None = None,
    plan_key: str | None = None,
) -> dict[str, Any]:
    ensure_initialized()
    existing = get_customer_account(clerk_user_id) or {}
    now = utc_now()
    payload = {
        "clerk_user_id": clerk_user_id,
        "email": email if email is not None else existing.get("email"),
        "full_name": full_name if full_name is not None else existing.get("full_name"),
        "buyer_type": buyer_type if buyer_type is not None else existing.get("buyer_type", "hedge_fund"),
        "organization_name": (
            organization_name if organization_name is not None else existing.get("organization_name", "")
        ),
        "onboarding_notes": (
            onboarding_notes if onboarding_notes is not None else existing.get("onboarding_notes", "")
        ),
        "stripe_customer_id": (
            stripe_customer_id if stripe_customer_id is not None else existing.get("stripe_customer_id")
        ),
        "stripe_subscription_id": (
            stripe_subscription_id
            if stripe_subscription_id is not None
            else existing.get("stripe_subscription_id")
        ),
        "stripe_price_id": stripe_price_id if stripe_price_id is not None else existing.get("stripe_price_id"),
        "stripe_product_name": (
            stripe_product_name if stripe_product_name is not None else existing.get("stripe_product_name")
        ),
        "subscription_status": (
            subscription_status if subscription_status is not None else existing.get("subscription_status", "inactive")
        ),
        "plan_key": plan_key if plan_key is not None else existing.get("plan_key", "free"),
        "created_at": existing.get("created_at", now),
        "updated_at": now,
    }

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO customer_accounts(
                clerk_user_id, email, full_name, buyer_type, organization_name,
                onboarding_notes, stripe_customer_id, stripe_subscription_id,
                stripe_price_id, stripe_product_name, subscription_status, plan_key,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(clerk_user_id) DO UPDATE SET
                email=excluded.email,
                full_name=excluded.full_name,
                buyer_type=excluded.buyer_type,
                organization_name=excluded.organization_name,
                onboarding_notes=excluded.onboarding_notes,
                stripe_customer_id=excluded.stripe_customer_id,
                stripe_subscription_id=excluded.stripe_subscription_id,
                stripe_price_id=excluded.stripe_price_id,
                stripe_product_name=excluded.stripe_product_name,
                subscription_status=excluded.subscription_status,
                plan_key=excluded.plan_key,
                updated_at=excluded.updated_at
            """,
            (
                payload["clerk_user_id"],
                payload["email"],
                payload["full_name"],
                payload["buyer_type"],
                payload["organization_name"],
                payload["onboarding_notes"],
                payload["stripe_customer_id"],
                payload["stripe_subscription_id"],
                payload["stripe_price_id"],
                payload["stripe_product_name"],
                payload["subscription_status"],
                payload["plan_key"],
                payload["created_at"],
                payload["updated_at"],
            ),
        )

    return payload


def create_alert_destination(
    clerk_user_id: str,
    label: str,
    channel: str,
    destination: str,
    min_score: float = 0.7,
    confirmed_only: bool = True,
    buyer_type: str | None = None,
    active: bool = True,
) -> dict[str, Any]:
    ensure_initialized()
    now = utc_now()
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO alert_destinations(
                clerk_user_id, label, channel, destination, min_score, confirmed_only,
                buyer_type, active, last_sent_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                clerk_user_id,
                label,
                channel,
                destination,
                float(min_score),
                1 if confirmed_only else 0,
                buyer_type,
                1 if active else 0,
                None,
                now,
                now,
            ),
        )
        alert_id = int(cur.lastrowid)
    return {
        "alert_id": alert_id,
        "clerk_user_id": clerk_user_id,
        "label": label,
        "channel": channel,
        "destination": destination,
        "min_score": float(min_score),
        "confirmed_only": bool(confirmed_only),
        "buyer_type": buyer_type,
        "active": bool(active),
        "last_sent_at": None,
        "created_at": now,
        "updated_at": now,
    }


def list_alert_destinations(clerk_user_id: str) -> list[dict[str, Any]]:
    ensure_initialized()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT alert_id, clerk_user_id, label, channel, destination, min_score,
                   confirmed_only, buyer_type, active, last_sent_at, created_at, updated_at
            FROM alert_destinations
            WHERE clerk_user_id = ?
            ORDER BY updated_at DESC, alert_id DESC
            """,
            (clerk_user_id,),
        ).fetchall()
    return [
        {
            "alert_id": row["alert_id"],
            "clerk_user_id": row["clerk_user_id"],
            "label": row["label"],
            "channel": row["channel"],
            "destination": row["destination"],
            "min_score": float(row["min_score"]),
            "confirmed_only": bool(row["confirmed_only"]),
            "buyer_type": row["buyer_type"],
            "active": bool(row["active"]),
            "last_sent_at": row["last_sent_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def mark_alert_sent(alert_id: int) -> None:
    ensure_initialized()
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            UPDATE alert_destinations
            SET last_sent_at = ?, updated_at = ?
            WHERE alert_id = ?
            """,
            (now, now, alert_id),
        )


def generate_brief_prompt(
    signals: list[dict[str, Any]],
    events: list[dict[str, Any]],
    watchlist: dict[str, Any] | None,
    portfolio: dict[str, Any] | None,
) -> str:
    lines = [
        "You are ORION, a private macro-quant research analyst.",
        "Write a concise but high-signal daily brief for a sophisticated investor.",
        "Use plain English. Organize around market regime, top signals, watchlist implications, and portfolio actions.",
        "Do not fabricate data not present below.",
        "",
        "Signals:",
    ]
    for signal in signals[:10]:
        lines.append(
            f"- {signal['asset']} score={signal.get('adjusted_score', signal.get('score_norm')):.3f} "
            f"path={signal.get('why_path', '')} lag={signal.get('when_months', 0)} confirmed={signal.get('confirmed')}"
        )
    lines.append("")
    lines.append("Events:")
    for event in events[:8]:
        lines.append(
            f"- [{event.get('event_type')}] {event.get('headline') or event.get('rationale')} "
            f"confidence={event.get('confidence', 0):.2f}"
        )
    lines.append("")
    if watchlist:
        lines.append(f"Watchlist assets: {', '.join(watchlist.get('assets', [])) or '(empty)'}")
    if portfolio:
        positions = portfolio.get("positions", [])[:8]
        lines.append(
            "Current portfolio recommendation: "
            + ", ".join(f"{p['asset']} {p['weight']:.1%}" for p in positions)
        )
    lines.append("")
    lines.append("Output format:")
    lines.append("1. Regime")
    lines.append("2. What matters now")
    lines.append("3. Watchlist focus")
    lines.append("4. Portfolio actions")
    return "\n".join(lines)


def generate_brief_with_ollama(prompt: str) -> str | None:
    base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    model = os.getenv("OLLAMA_BRIEF_MODEL") or os.getenv("OLLAMA_MODEL") or "gemma3:4b"
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as res:
            data = json.loads(res.read().decode("utf-8"))
            return data.get("response")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None
