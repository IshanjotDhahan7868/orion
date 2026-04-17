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
