# orion/scripts/week6_market_check.py
from __future__ import annotations

import os
import sys
from pathlib import Path
import yaml
import pandas as pd

from orion.market.market_data import fetch_ohlcv, compute_features
from orion.market.filters import confirm_and_rescore


# ----------------------------
# Robust paths (match Week 5)
# ----------------------------
BASE_DIR = Path(__file__).resolve().parents[1]   # .../orion/
CFG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"

IN_SIGNALS = PROCESSED_DIR / "signals.csv"
OUT_SIGNALS = PROCESSED_DIR / "signals_week6.csv"

# mild penalty for "unconfirmable" assets (skipped/missing)
UNCONFIRMABLE_PENALTY_MULT = 0.90


def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_symbol(asset: str, mapped) -> tuple[str, str, str]:
    """
    Returns (symbol, market_status, reason)
      market_status: ok | skipped | missing
    """
    # If mapping is explicitly null/None -> skip with reason (e.g., SILICON: null)
    if mapped is None:
        return "", "skipped", "no_liquid_proxy"

    # If mapping exists and non-empty string -> use it
    if isinstance(mapped, str) and mapped.strip():
        return mapped.strip(), "ok", "mapped"

    # Robust fallback: if asset itself looks like a ticker, use it
    # (allow slightly longer, because you may have ETF tickers like "SOXX")
    if isinstance(asset, str) and asset.isupper() and 3 <= len(asset) <= 8:
        return asset, "ok", "fallback_symbol_equal_asset"

    # Otherwise missing
    return "", "missing", "no_mapping_found"


def main():
    if not IN_SIGNALS.exists():
        print(f"Missing {IN_SIGNALS}. Run Week 5 first.")
        sys.exit(1)

    sigs = pd.read_csv(IN_SIGNALS)

    # Prefer latest batch if available; else use the latest event_id
    if "batch_id" in sigs.columns and sigs["batch_id"].notna().any():
        latest_batch = sigs["batch_id"].dropna().astype(str).iloc[-1]
        df = sigs[sigs["batch_id"].astype(str) == str(latest_batch)].copy()
    else:
        latest_event = sigs["event_id"].iloc[-1]
        df = sigs[sigs["event_id"] == latest_event].copy()

    # Dedupe per asset (keep the most recent row for each asset)
    df = df.drop_duplicates(subset=["asset"], keep="first").copy()

    # Load maps/meta (anchored)
    assets_meta = load_yaml(CFG_DIR / "assets.yaml") or {}
    market_map = load_yaml(CFG_DIR / "market_map.yaml") or {}

    print("Assets from Week5 batch:", sorted(df["asset"].unique()))

    # Map asset -> symbol and add status + reason
    symbols, statuses, reasons = [], [], []
    for asset in df["asset"].tolist():
        sym, st, rsn = resolve_symbol(asset, market_map.get(asset))
        symbols.append(sym)
        statuses.append(st)
        reasons.append(rsn)

    df["symbol"] = symbols
    df["market_status"] = statuses
    df["reason"] = reasons

    print("Mapped symbols/status:", df[["asset", "symbol", "market_status", "reason"]].to_dict(orient="records"))

    ok_df = df[df["symbol"] != ""].copy()
    skip_df = df[df["symbol"] == ""].copy()  # skipped or missing

    # If nothing is market-confirmable, still write output with transparency
    if ok_df.empty:
        print("No assets had usable market symbols. Writing transparent skipped output.")
        out = skip_df.copy()
        out["confirm_score"] = 0.0
        out["penalty"] = 0.0
        out["adj_score"] = out["score_norm"] * UNCONFIRMABLE_PENALTY_MULT
        OUT_SIGNALS.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(OUT_SIGNALS, index=False)
        print(f"Saved: {OUT_SIGNALS}")
        sys.exit(0)

    # Build symbol list to fetch (+ benchmarks)
    symbols_to_fetch = sorted(set(ok_df["symbol"].tolist() + ["SPY", "QQQ"]))

    # Cached market features by symbol
    prices = fetch_ohlcv(symbols_to_fetch, use_cache=True)
    feats_by_symbol = compute_features(prices)  # index = symbol (ticker)

    feats_by_symbol = feats_by_symbol.reset_index().rename(columns={"asset": "symbol"})
    merged = ok_df.merge(feats_by_symbol, on="symbol", how="left")

    # Prepare market features indexed by original asset name for confirm_and_rescore
    feats_by_asset = merged.set_index("asset")[[
        "price", "ma50", "ma200", "vol_z20",
        "r_1m", "r_3m", "rs_1m", "rs_3m",
        "above_ma50", "above_ma200", "golden"
    ]]

    # Pass market_status/reason through into signals_in so they survive
    signals_in_cols = [
        "event_id", "asset", "rank", "score_raw", "score_norm",
        "why_path", "when_months", "symbol", "market_status", "reason"
    ]
    signals_in = merged[signals_in_cols]

    out_ok, _flags = confirm_and_rescore(signals_in, feats_by_asset, assets_meta)

    # Build skipped output rows (transparent)
    if not skip_df.empty:
        out_skip = skip_df.copy()

        # Ensure same columns exist
        for col in ["confirm_rs1m", "confirm_rs3m", "confirm_trend", "confirm_vol", "confirm_score", "penalty", "adj_score"]:
            if col not in out_skip.columns:
                out_skip[col] = 0.0

        # Apply mild penalty because we cannot market-confirm
        out_skip["adj_score"] = out_skip["score_norm"] * UNCONFIRMABLE_PENALTY_MULT

        # Add empty feature columns (so CSV schema is stable)
        for col in ["price", "ma50", "ma200", "vol_z20", "r_1m", "r_3m", "rs_1m", "rs_3m",
                    "above_ma50", "above_ma200", "golden"]:
            if col not in out_skip.columns:
                out_skip[col] = pd.NA

        # Align columns to out_ok
        out = pd.concat(
            [out_ok, out_skip[out_ok.columns.intersection(out_skip.columns).tolist()]],
            ignore_index=True
        )
    else:
        out = out_ok

    # Rank & save
    out = out.sort_values(["event_id", "adj_score"], ascending=[True, False])
    out = out.drop_duplicates(subset=["asset"], keep="first")
    OUT_SIGNALS.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_SIGNALS, index=False)

    # Display top-10
    cols = [
        "asset", "symbol", "market_status", "reason",
        "score_norm", "adj_score",
        "rs_1m", "rs_3m", "above_ma50", "golden", "vol_z20",
        "why_path", "when_months"
    ]
    print("\n--- WEEK 6: Market-checked signals (top 10) ---")
    existing_cols = [c for c in cols if c in out.columns]
    print(out[existing_cols].head(10).to_string(index=False))
    print(f"\nSaved: {OUT_SIGNALS}")


if __name__ == "__main__":
    main()
