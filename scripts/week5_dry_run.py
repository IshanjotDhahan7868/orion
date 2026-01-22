# orion/scripts/week5_dry_run.py
from __future__ import annotations

from pathlib import Path
import csv
import datetime as dt
import os
import yaml

from orion.graph.dependency_graph import DependencyGraph
from orion.graph.propagate import propagate_impact
from orion.graph.asset_impact import aggregate_assets


# ----------------------------
# Path helpers (robust)
# ----------------------------
BASE_DIR = Path(__file__).resolve().parents[1]         # .../orion/
CFG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"


def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def try_load_latest_event() -> dict | None:
    """
    Best-effort: load a real Week-4 event if present.
    Supported (first match wins):
      - data/processed/events.jsonl  (each line is a JSON object)
      - data/processed/events.yaml   (list or dict)
      - data/processed/events.yml
      - data/processed/events.csv    (expects 'event_id' + 'entities' JSON column OR columns like companies/technologies)
    Returns: event dict or None
    """
    import json
    candidates = [
        PROCESSED_DIR / "events.jsonl",
        PROCESSED_DIR / "events.yaml",
        PROCESSED_DIR / "events.yml",
        PROCESSED_DIR / "events.csv",
    ]

    for p in candidates:
        if not p.exists():
            continue

        try:
            if p.suffix == ".jsonl":
                # take last non-empty line
                lines = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
                if not lines:
                    continue
                return json.loads(lines[-1])

            if p.suffix in (".yaml", ".yml"):
                obj = load_yaml(p)
                # If it's a list of events, take last; if dict, assume it's an event
                if isinstance(obj, list) and obj:
                    return obj[-1]
                if isinstance(obj, dict) and obj:
                    return obj
                continue

            if p.suffix == ".csv":
                import pandas as pd
                df = pd.read_csv(p)
                if df.empty:
                    continue
                row = df.iloc[-1].to_dict()

                # If entities is a JSON string column, parse it
                if "entities" in row and isinstance(row["entities"], str) and row["entities"].strip():
                    try:
                        row["entities"] = json.loads(row["entities"])
                    except Exception:
                        pass

                # If entities missing, try reconstruct from common columns
                if "entities" not in row or not isinstance(row["entities"], dict):
                    entities = {"companies": [], "technologies": []}
                    for col in ("companies", "company", "company_list"):
                        if col in row and isinstance(row[col], str) and row[col].strip():
                            entities["companies"] = [x.strip() for x in row[col].split("|") if x.strip()]
                    for col in ("technologies", "technology", "tech_list"):
                        if col in row and isinstance(row[col], str) and row[col].strip():
                            entities["technologies"] = [x.strip() for x in row[col].split("|") if x.strip()]
                    row["entities"] = entities

                if "event_id" not in row or not row["event_id"]:
                    row["event_id"] = "latest_from_events_csv"

                return row

        except Exception:
            # If one format fails, try the next candidate
            continue

    return None


# ----------------------------
# Event → node mapping (same logic you already had)
# ----------------------------
def map_event_to_nodes(event: dict, company_map: dict, tech_map: dict) -> list[str]:
    injected_nodes = set()

    entities = event.get("entities", {}) or {}
    companies = entities.get("companies", []) or []
    technologies = entities.get("technologies", []) or []

    for company in companies:
        if company in company_map:
            injected_nodes.update(company_map[company].get("nodes", []) or [])

    for tech in technologies:
        if tech in tech_map:
            injected_nodes.update(tech_map[tech].get("nodes", []) or [])

    return list(injected_nodes)


def main() -> None:
    # 1) Load graph + mappings using absolute paths
    graph_path = CFG_DIR / "graph.yaml"
    assets_path = CFG_DIR / "assets.yaml"
    companies_path = CFG_DIR / "companies.yaml"
    tech_path = CFG_DIR / "technologies.yaml"

    if not graph_path.exists():
        raise FileNotFoundError(f"Missing: {graph_path}")
    if not assets_path.exists():
        raise FileNotFoundError(f"Missing: {assets_path}")
    if not companies_path.exists():
        raise FileNotFoundError(f"Missing: {companies_path}")
    if not tech_path.exists():
        raise FileNotFoundError(f"Missing: {tech_path}")

    graph = DependencyGraph.from_yaml(str(graph_path))

    asset_map = load_yaml(assets_path) or {}
    company_map = load_yaml(companies_path) or {}
    tech_map = load_yaml(tech_path) or {}

    # DEBUG
    print("All graph node IDs:", list(graph.nodes))
    print("Asset mappings:")
    for asset, meta in (asset_map or {}).items():
        if isinstance(meta, dict):
            print(f"  {asset}: {meta.get('nodes', [])}")

    # 2) Load an event (real if possible, else fallback demo)
    event = try_load_latest_event()
    if event is None:
        event = {
            "event_id": "test",
            "entities": {"companies": ["TSM"], "technologies": ["advanced_chips"]},
        }
        print("\n[week5] No events file found in data/processed/. Using demo event:", event)
    else:
        print("\n[week5] Using latest event from data/processed/:")
        print(event)

    # 3) Inject and propagate
    start_nodes = map_event_to_nodes(event, company_map, tech_map)
    print("\nInjected nodes from event:", start_nodes)

    node_impacts, best_node_paths = propagate_impact(graph, start_nodes)
    print("Node impacts after propagation:", dict(node_impacts))

    # 4) Aggregate to assets (ETF de-bias + exposure normalization)
    type_weights = {"equity": 1.0, "etf": 0.6, "commodity": 0.9}
    asset_scores, asset_meta = aggregate_assets(
        node_impacts, asset_map, best_node_paths, type_weights=type_weights
    )
    print("Asset scores (pre-ranking):", asset_scores)

    # 5) Rank top 10 and print why/when
    signals = sorted(asset_scores.items(), key=lambda x: x[1], reverse=True)[:10]
    top_score = signals[0][1] if signals else 1.0

    print("\n--- TOP ASSET SIGNALS ---")
    for rank, (asset, score) in enumerate(signals, start=1):
        meta = asset_meta.get(asset)
        why_path = " → ".join(meta["path"]) if meta and meta.get("path") else ""
        when_months = meta.get("lag_months", 0) if meta else 0
        print({
            "event_id": event.get("event_id", ""),
            "asset": asset,
            "rank": rank,
            "score_raw": round(score, 6),
            "score_norm": round(score / top_score, 6) if top_score else 0,
            "why_path": why_path,
            "when_months": when_months,
        })

    # 6) Save to CSV (for Week 6)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    outfile = PROCESSED_DIR / "signals.csv"

    header = [
        "event_id", "asset", "rank", "score_raw", "score_norm",
        "why_path", "when_months", "graph_version", "created_at", "batch_id"
    ]

    write_header = not outfile.exists()
    # One timestamp for the whole batch (Week 6 selects the batch)
    batch_id = dt.datetime.now(dt.UTC).isoformat()

    with open(outfile, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(header)

        for rank, (asset, score) in enumerate(signals, start=1):
            meta = asset_meta.get(asset) or {}
            why_path = " → ".join(meta.get("path", [])) if meta.get("path") else ""
            when_months = meta.get("lag_months", 0) if meta else 0

            w.writerow([
                event.get("event_id", ""),
                asset,
                rank,
                round(score, 6),
                round(score / top_score, 6) if top_score else 0,
                why_path,
                when_months,
                "v1.1",
                batch_id,
                batch_id,
            ])

    print(f"Saved {len(signals)} signals to {outfile}")


if __name__ == "__main__":
    main()
