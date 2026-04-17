"""Backtest utilities for ORION signal artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def load_signals(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "signals" in data:
        data = data["signals"]
    return pd.DataFrame(data)


def simulate_holding_window(
    signals: pd.DataFrame,
    market_prices: pd.DataFrame,
    hold_days: int = 5,
    score_col: str = "adj_score",
) -> pd.DataFrame:
    """Replay signal dates against future prices.

    market_prices columns: date, asset, close
    signals columns: asset, timestamp (or published_at), score_col
    """
    df = signals.copy()
    time_col = "timestamp" if "timestamp" in df.columns else "published_at"
    df["signal_date"] = pd.to_datetime(df[time_col]).dt.normalize()

    px = market_prices.copy()
    px["date"] = pd.to_datetime(px["date"]).dt.normalize()
    px = px.sort_values(["asset", "date"])

    out_rows = []
    for row in df.itertuples(index=False):
        asset_px = px[px["asset"] == row.asset]
        after = asset_px[asset_px["date"] >= row.signal_date]
        if after.empty:
            continue

        start_idx = after.index[0]
        seq = asset_px.loc[start_idx:]
        if len(seq) <= hold_days:
            continue

        entry = float(seq.iloc[0]["close"])
        exit_ = float(seq.iloc[hold_days]["close"])
        ret = (exit_ / entry) - 1.0
        out_rows.append(
            {
                "asset": row.asset,
                "signal_date": row.signal_date,
                "score": float(getattr(row, score_col, 0.0) or 0.0),
                "entry": entry,
                "exit": exit_,
                "return": ret,
            }
        )

    return pd.DataFrame(out_rows)


def summary_metrics(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {
            "num_trades": 0,
            "hit_rate": 0.0,
            "avg_return": 0.0,
            "cum_return": 0.0,
            "drawdown_proxy": 0.0,
        }

    rets = trades["return"].astype(float)
    equity = (1 + rets).cumprod()
    peak = equity.cummax()
    dd = (equity / peak) - 1.0

    return {
        "num_trades": int(len(trades)),
        "hit_rate": float((rets > 0).mean()),
        "avg_return": float(rets.mean()),
        "cum_return": float(equity.iloc[-1] - 1.0),
        "drawdown_proxy": float(dd.min()),
    }
