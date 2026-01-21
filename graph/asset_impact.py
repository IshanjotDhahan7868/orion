"""
Aggregate node impacts into asset scores with:
- explicit asset types (equity/etf/commodity)
- exposure normalization (avoid "broad basket always wins")
- best-path metadata for explanations/time window
"""

DEFAULT_TYPE_WEIGHTS = {"equity": 1.0, "etf": 0.6, "commodity": 0.9}

def aggregate_assets(node_impacts, asset_map, best_node_paths, type_weights=None):
    type_weights = type_weights or DEFAULT_TYPE_WEIGHTS
    asset_scores = {}
    asset_meta = {}

    for asset, meta in asset_map.items():
        nodes = meta.get("nodes", []) or []
        if not nodes:
            continue

        atype = (meta.get("type") or "equity").lower()
        type_w = type_weights.get(atype, 1.0)

        # normalize by number of nodes to avoid "broader exposure always on top"
        exposure_norm = max(1, len(nodes))

        score = 0.0
        best_expl = None  # strongest contributing node path for explanations

        for node in nodes:
            s = node_impacts.get(node, 0.0)
            if s <= 0:
                continue
            score += s

            np = best_node_paths.get(node)
            if np and (best_expl is None or np["strength"] > best_expl["strength"]):
                best_expl = np  # {"path":[...], "strength":x, "lag_months":y}

        if score > 0:
            asset_scores[asset] = (score / exposure_norm) * type_w
            asset_meta[asset] = best_expl

    return asset_scores, asset_meta
