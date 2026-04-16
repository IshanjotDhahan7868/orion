"""Learning/reporting scaffolds for ORION graph evolution."""

from __future__ import annotations

import pandas as pd


def compare_predicted_vs_realized(
    trades: pd.DataFrame,
    score_col: str = "score",
    return_col: str = "return",
    n_buckets: int = 5,
) -> pd.DataFrame:
    """Bucket predictions and compare realized outcomes."""
    if trades.empty:
        return pd.DataFrame(columns=["bucket", "count", "avg_score", "avg_return"])

    df = trades[[score_col, return_col]].dropna().copy()
    if df.empty:
        return pd.DataFrame(columns=["bucket", "count", "avg_score", "avg_return"])

    df["bucket"] = pd.qcut(df[score_col], q=min(n_buckets, len(df)), duplicates="drop")
    report = (
        df.groupby("bucket", observed=True)
        .agg(count=(score_col, "size"), avg_score=(score_col, "mean"), avg_return=(return_col, "mean"))
        .reset_index()
    )
    return report


def suggest_edge_weight_adjustments(
    attribution_df: pd.DataFrame,
    min_samples: int = 5,
    step: float = 0.05,
) -> list[dict]:
    """Suggest non-destructive edge-weight adjustment candidates.

    attribution_df columns: edge_id, predicted_contrib, realized_return
    """
    if attribution_df.empty:
        return []

    out: list[dict] = []
    grouped = attribution_df.groupby("edge_id", observed=True)
    for edge_id, grp in grouped:
        if len(grp) < min_samples:
            continue

        corr = grp["predicted_contrib"].corr(grp["realized_return"])
        if pd.isna(corr):
            continue

        action = "increase" if corr > 0 else "decrease"
        confidence = min(1.0, abs(float(corr)))
        out.append(
            {
                "edge_id": edge_id,
                "action": action,
                "step": step,
                "confidence": confidence,
                "sample_size": int(len(grp)),
                "reason": f"corr(predicted,realized)={corr:.3f}",
            }
        )

    return sorted(out, key=lambda x: (x["confidence"], x["sample_size"]), reverse=True)


def build_learning_report(trades: pd.DataFrame, attribution_df: pd.DataFrame) -> dict:
    return {
        "bucket_analysis": compare_predicted_vs_realized(trades).to_dict(orient="records"),
        "edge_adjustment_candidates": suggest_edge_weight_adjustments(attribution_df),
    }
