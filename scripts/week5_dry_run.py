from graph.dependency_graph import DependencyGraph
from graph.propagate import propagate_impact
from graph.asset_impact import aggregate_assets
import csv, os, datetime as dt
import yaml

# 1) Load graph
graph = DependencyGraph.from_yaml("config/graph.yaml")

# 2) Load mappings
with open("config/assets.yaml") as f:
    asset_map = yaml.safe_load(f)
with open("config/companies.yaml") as f:
    company_map = yaml.safe_load(f)
with open("config/technologies.yaml") as f:
    tech_map = yaml.safe_load(f)

# DEBUG
print("All graph node IDs:", list(graph.nodes))
print("Asset mappings:")
for asset, meta in asset_map.items():
    print(f"  {asset}: {meta.get('nodes', [])}")

# 3) Event→node mapping (inline)
def map_event_to_nodes(event, company_map, tech_map):
    injected_nodes = set()
    for company in event["entities"].get("companies", []):
        if company in company_map:
            injected_nodes.update(company_map[company].get("nodes", []))
    for tech in event["entities"].get("technologies", []):
        if tech in tech_map:
            injected_nodes.update(tech_map[tech].get("nodes", []))
    return list(injected_nodes)

# Example event (swap in real Week-4 event)
event = {
    "event_id": "test",
    "entities": {
        "companies": ["TSM"],
        "technologies": ["advanced_chips"]
    }
}

# 4) Inject and propagate
start_nodes = map_event_to_nodes(event, company_map, tech_map)
print("\nInjected nodes from event:", start_nodes)

node_impacts, best_node_paths = propagate_impact(graph, start_nodes)
print("Node impacts after propagation:", dict(node_impacts))

# 5) Aggregate to assets (ETF de-bias + exposure normalization)
type_weights = {"equity": 1.0, "etf": 0.6, "commodity": 0.9}
asset_scores, asset_meta = aggregate_assets(node_impacts, asset_map, best_node_paths, type_weights=type_weights)
print("Asset scores (pre-ranking):", asset_scores)

# 6) Normalize scores 0–1 and print top 10 with "why/when"
signals = sorted(asset_scores.items(), key=lambda x: x[1], reverse=True)[:10]
max_s = max((score for _, score in signals), default=1.0)

print("\n--- TOP ASSET SIGNALS ---")
for rank, (asset, score) in enumerate(signals, start=1):
    meta = asset_meta.get(asset)
    why = " → ".join(meta["path"]) if meta else "N/A"
    when = f'~{meta["lag_months"]}m' if meta else "N/A"
    print({
        "event_id": event["event_id"],
        "asset": asset,
        "rank": rank,
        "score_raw": round(score, 4),
        "score_norm": round(score / max_s, 4),
        "why": why,   # strongest causal path to an exposed node
        "when": when  # summed lag months along that path
    })


# 7) Save to CSV (for later ingestion) 
os.makedirs("data/processed", exist_ok=True)
outfile = "data/processed/signals.csv"
header = ["event_id","asset","rank","score_raw","score_norm","why_path","when_months","graph_version","created_at"]

write_header = not os.path.exists(outfile)
with open(outfile, "a", newline="") as f:
    w = csv.writer(f)
    if write_header: w.writerow(header)
    top_score = signals[0][1] if signals else 1.0
    for rank, (asset, score) in enumerate(signals, start=1):
        meta = asset_meta.get(asset)
        why = " → ".join(meta["path"]) if meta else ""
        when = meta["lag_months"] if meta else 0
        w.writerow([
            event["event_id"], asset, rank,
            round(score, 6), round(score/top_score, 6),
            why, when,
            "v1.1", dt.datetime.utcnow().isoformat()
        ])
print(f"Saved {len(signals)} signals to {outfile}")
