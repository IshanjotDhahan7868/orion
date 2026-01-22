# orion/market/filters.py
from __future__ import annotations

import re
from typing import Dict, List, Tuple

import pandas as pd

# Conservative defaults; adjust as you like
DEFAULT_THRESH = {
    "min_rs_1m": 0.00,   # >= 0% vs bench in 1m
    "min_rs_3m": -0.02,  # >= -2% vs bench in 3m
    "min_vol_z": -0.20,  # avoid dead volume
}


def build_flags(asset_type: str, why_path: str) -> Dict[str, bool]:
    """
    Simple risk flags you can expand later.
    """
    why_path = why_path or ""
    crowded = (asset_type == "etf")
    regulatory = bool(re.search(r"Trade_Restrictions|Regulation|Export", why_path))
    cyclical = bool(re.search(r"Oil_and_Gas|Industrial_Construction|Cyclical", why_path))
    return {"crowded": crowded, "regulatory": regulatory, "cyclical": cyclical}


def _ensure_asset_column(market_df: pd.DataFrame) -> pd.DataFrame:
    """
    Make market_df mergeable on 'asset'. Supports:
    - index named 'asset'
    - index named something else
    - already has 'asset' column
    """
    m = market_df.copy()

    if "asset" in m.columns:
        return m

    m = m.reset_index()
    # rename first column to 'asset' if needed
    if m.columns[0] != "asset":
        m = m.rename(columns={m.columns[0]: "asset"})
    return m


def confirm_and_rescore(
    signals_df: pd.DataFrame,
    market_df: pd.DataFrame,
    assets_meta: dict,
    thresholds: dict | None = None,
    alpha_confirm: float = 0.25,
    beta_penalty: float = 0.20,
) -> Tuple[pd.DataFrame, List[Dict[str, bool]]]:
    """
    Inputs:
      signals_df: rows per asset with at least:
        - asset, score_norm
        - why_path (optional but recommended)
      market_df: features indexed by asset OR with an 'asset' column:
        - rs_1m, rs_3m, above_ma50, golden, vol_z20, etc.
      assets_meta: loaded assets.yaml mapping asset -> {type: equity/etf/commodity...}

    Returns:
      (out_df, flags_list)
    """
    thresholds = thresholds or DEFAULT_THRESH

    m = _ensure_asset_column(market_df)

    df = signals_df.merge(m, on="asset", how="left")

    # ---- confirmations (NaN-safe) ----
    df["confirm_rs1m"] = (df.get("rs_1m", pd.Series([pd.NA]*len(df))) >= thresholds["min_rs_1m"]).fillna(False).astype(int)
    df["confirm_rs3m"] = (df.get("rs_3m", pd.Series([pd.NA]*len(df))) >= thresholds["min_rs_3m"]).fillna(False).astype(int)

    above_ma50 = df.get("above_ma50", 0).fillna(0).astype(int)
    golden = df.get("golden", 0).fillna(0).astype(int)
    df["confirm_trend"] = (above_ma50 & golden).astype(int)

    df["confirm_vol"] = (df.get("vol_z20", pd.Series([pd.NA]*len(df))) >= thresholds["min_vol_z"]).fillna(False).astype(int)

    # Weighted confirmation score
    df["confirm_score"] = (
        0.35 * df["confirm_rs1m"]
        + 0.25 * df["confirm_rs3m"]
        + 0.25 * df["confirm_trend"]
        + 0.15 * df["confirm_vol"]
    )

    # ---- risk flags / penalty ----
    flags: List[Dict[str, bool]] = []
    penalties: List[float] = []

    for _, row in df.iterrows():
        meta = assets_meta.get(row["asset"], {}) if isinstance(assets_meta, dict) else {}
        asset_type = str(meta.get("type", "equity")).lower()

        f = build_flags(asset_type=asset_type, why_path=row.get("why_path", "") or "")
        penalty = 0.0
        if f["regulatory"]:
            penalty += 0.15
        if f["cyclical"]:
            penalty += 0.10
        if f["crowded"]:
            penalty += 0.10

        flags.append(f)
        penalties.append(penalty)

    df["penalty"] = penalties

    # ---- adjusted score ----
    # bump by confirmations, reduce by penalty
    df["adj_score"] = (
        df["score_norm"].astype(float)
        * (1.0 + alpha_confirm * df["confirm_score"].astype(float))
        * (1.0 - beta_penalty * df["penalty"].astype(float))
    )

    return df, flags
