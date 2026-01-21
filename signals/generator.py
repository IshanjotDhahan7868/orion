def generate_signals(event, asset_scores, asset_paths, top_n=10):
    ranked = sorted(
        asset_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )[:top_n]

    signals = []

    for rank, (asset, score) in enumerate(ranked, start=1):
        signals.append({
            "event_id": event["event_id"],
            "asset": asset,
            "rank": rank,
            "score": round(score, 4),
            "explanation": (
                f"Event propagated through nodes: "
                f"{' → '.join(asset_paths[asset])}"
            )
        })

    return signals
