# orion/market/market_data.py
from __future__ import annotations

import datetime as dt
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf

from orion.market.cache import YahooDailyCache

DEFAULT_BENCH = ["SPY", "QQQ"]


def _period_start(days: int) -> str:
    return (dt.date.today() - dt.timedelta(days=days)).isoformat()


def _normalize_single_ticker_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize a single-ticker yfinance df to:
      index: DatetimeIndex
      columns: Open, High, Low, Close, Volume
    Works whether yfinance returns single-level columns or MultiIndex columns.
    """
    if df is None or len(df) == 0:
        return pd.DataFrame()

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    # ✅ KEY FIX: yfinance may return MultiIndex columns even for a single ticker:
    # [('Close','SPY'), ('Open','SPY'), ...]
    # Flatten to just field names: ['Close','Open',...]
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Handle Adj Close edge-case
    if "Close" not in df.columns and "Adj Close" in df.columns:
        df = df.rename(columns={"Adj Close": "Close"})

    keep_order = ["Open", "High", "Low", "Close", "Volume"]
    keep = [c for c in keep_order if c in df.columns]
    return df[keep].copy()




def _assemble_field_ticker_matrix(per_ticker: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Build MultiIndex columns (Field, Ticker) from per-ticker single-level dfs.
    """
    parts = {}
    for t, df in per_ticker.items():
        if df is None or df.empty:
            continue
        for field in df.columns:
            parts[(field, t)] = df[field]

    if not parts:
        return pd.DataFrame()

    out = pd.concat(parts, axis=1)
    out.columns = pd.MultiIndex.from_tuples(out.columns, names=["Field", "Ticker"])
    out = out.sort_index(axis=1)
    out = out.sort_index()
    return out


def fetch_ohlcv(
    tickers: List[str],
    start: str | None = None,
    end: str | None = None,
    use_cache: bool = True,
    cache_asof: Optional[str] = None,
) -> pd.DataFrame:
    """
    Cache-first OHLCV pull.

    Returns a MultiIndex columns df: (Field, Ticker),
    where Field includes Close + Volume at minimum for feature computation.
    """
    if end is None:
        end = dt.date.today().isoformat()
    if start is None:
        start = _period_start(540)  # enough history for 200dma

    tickers = [t.strip() for t in tickers if isinstance(t, str) and t.strip()]
    if not tickers:
        raise ValueError("fetch_ohlcv: empty tickers list")

    cache = YahooDailyCache() if use_cache else None

    per_ticker: Dict[str, pd.DataFrame] = {}
    missing: List[str] = []

    # 1) Try cache
    for t in tickers:
        if cache is None:
            missing.append(t)
            continue
        cached = cache.load(t, start=start, end=end, asof=cache_asof)
        if cached is None or cached.empty:
            missing.append(t)
        else:
            per_ticker[t] = _normalize_single_ticker_df(cached)

    # 2) Fetch misses individually (easy caching + simpler error handling)
    for t in missing:
        raw = yf.download(
            t,
            start=start,
            end=end,
            auto_adjust=True,
            progress=False,
            group_by="column",
        )
        df = _normalize_single_ticker_df(raw)
        per_ticker[t] = df

        # Save only if we actually have data
        if cache is not None and not df.empty:
            cache.save(t, start=start, end=end, df=df, asof=cache_asof)

    data = _assemble_field_ticker_matrix(per_ticker)
    if data is None or data.empty:
        raise ValueError("No price data available (no cache hits and no downloads).")

    # ✅ IMPORTANT FIX: select by level-0 field names in a MultiIndex
    desired_fields = ["Close", "Volume", "Open", "High", "Low"]
    lvl0 = data.columns.get_level_values(0)
    mask = lvl0.isin(desired_fields)
    data = data.loc[:, mask]

    # Ensure we at least have Close + Volume somewhere
    fields_present = set(data.columns.get_level_values(0).unique().tolist())
    if "Close" not in fields_present or "Volume" not in fields_present:
        # Helpful debug message
        raise ValueError(
            f"Price matrix missing required fields. Present fields={sorted(fields_present)}. "
            f"Tickers={tickers}"
        )

    return data


def compute_features(prices: pd.DataFrame, bench: List[str] = DEFAULT_BENCH) -> pd.DataFrame:
    fields = prices.columns.get_level_values(0).unique()
    if "Close" not in fields or "Volume" not in fields:
        raise ValueError("Expected Close and Volume in the price DataFrame")

    closes = prices["Close"]     # columns = tickers
    vols = prices["Volume"]      # columns = tickers

    # Moving averages
    ma50 = closes.rolling(50).mean()
    ma200 = closes.rolling(200).mean()

    # Volume z-score (20d)
    vol_mean = vols.rolling(20).mean()
    vol_std = vols.rolling(20).std(ddof=0).replace(0, np.nan)
    vol_z = (vols - vol_mean) / vol_std

    # Returns & RS (disable forward-fill)
    r_1m = closes.pct_change(21, fill_method=None).iloc[-1]
    r_3m = closes.pct_change(63, fill_method=None).iloc[-1]

    bench_list = [b for b in bench if b in closes.columns]
    if bench_list:
        b1m = r_1m[bench_list].mean()
        b3m = r_3m[bench_list].mean()
        rs_1m = r_1m - b1m
        rs_3m = r_3m - b3m
    else:
        rs_1m = pd.Series(0.0, index=closes.columns)
        rs_3m = pd.Series(0.0, index=closes.columns)

    latest = closes.index[-1]
    df = pd.DataFrame({
        "date": latest,
        "price": closes.iloc[-1],
        "ma50": ma50.iloc[-1],
        "ma200": ma200.iloc[-1],
        "vol_z20": vol_z.iloc[-1],
        "r_1m": r_1m,
        "r_3m": r_3m,
        "rs_1m": rs_1m,
        "rs_3m": rs_3m,
    })
    df.index.name = "asset"

    # Trend flags
    df["above_ma50"] = (df["price"] > df["ma50"]).astype(int)
    df["above_ma200"] = (df["price"] > df["ma200"]).astype(int)
    df["golden"] = (df["ma50"] > df["ma200"]).astype(int)

    return df
