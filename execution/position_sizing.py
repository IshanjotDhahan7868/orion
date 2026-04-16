"""Position sizing utilities.

Pure helper functions for translating signal strengths into portfolio weights.
"""

from __future__ import annotations

from collections import defaultdict


def _normalize_non_negative(values: dict[str, float]) -> dict[str, float]:
    clipped = {k: max(0.0, float(v)) for k, v in values.items()}
    total = sum(clipped.values())
    if total <= 0:
        return {k: 0.0 for k in clipped}
    return {k: v / total for k, v in clipped.items()}


def scores_to_target_weights(scores: dict[str, float], gross_exposure: float = 1.0) -> dict[str, float]:
    """Convert normalized scores to target portfolio weights.

    Example:
        >>> scores_to_target_weights({"AAPL": 0.6, "MSFT": 0.4})
        {'AAPL': 0.6, 'MSFT': 0.4}
    """
    weights = _normalize_non_negative(scores)
    return {k: v * max(0.0, min(1.0, gross_exposure)) for k, v in weights.items()}


def apply_asset_caps(weights: dict[str, float], max_per_asset: float = 0.10) -> dict[str, float]:
    return {k: min(max(0.0, w), max_per_asset) for k, w in weights.items()}


def apply_theme_caps(
    weights: dict[str, float],
    asset_to_theme: dict[str, str],
    max_per_theme: float = 0.30,
) -> dict[str, float]:
    """Cap cumulative weights by theme while preserving deterministic order."""
    out: dict[str, float] = {}
    used_by_theme: dict[str, float] = defaultdict(float)

    for asset, w in sorted(weights.items(), key=lambda x: x[1], reverse=True):
        theme = asset_to_theme.get(asset, "UNMAPPED")
        remaining = max(0.0, max_per_theme - used_by_theme[theme])
        applied = min(max(0.0, w), remaining)
        out[asset] = applied
        used_by_theme[theme] += applied

    return out


def renormalize(weights: dict[str, float], target_total: float = 1.0) -> dict[str, float]:
    """Rescale current weights to sum to <= target_total."""
    target_total = max(0.0, min(1.0, target_total))
    total = sum(max(0.0, v) for v in weights.values())
    if total <= 0:
        return {k: 0.0 for k in weights}
    if total <= target_total:
        return {k: max(0.0, v) for k, v in weights.items()}

    scale = target_total / total
    return {k: max(0.0, v) * scale for k, v in weights.items()}


def build_capped_weights(
    scores: dict[str, float],
    asset_to_theme: dict[str, str],
    max_per_asset: float = 0.10,
    max_per_theme: float = 0.30,
    gross_exposure: float = 1.0,
) -> dict[str, float]:
    """End-to-end capped weight construction."""
    w = scores_to_target_weights(scores, gross_exposure=gross_exposure)
    w = apply_asset_caps(w, max_per_asset=max_per_asset)
    w = apply_theme_caps(w, asset_to_theme=asset_to_theme, max_per_theme=max_per_theme)
    w = renormalize(w, target_total=gross_exposure)
    return w
