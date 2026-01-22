# market/cache.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd


def _today_str() -> str:
    return date.today().isoformat()


def _safe_ticker(ticker: str) -> str:
    # filesystem-safe name for yfinance tickers like "BRK-B", "^GSPC", "HG=F"
    t = ticker.strip().upper()
    t = t.replace("^", "")
    t = t.replace("/", "_")
    t = t.replace("=", "_")
    t = t.replace("-", "_")
    return t


@dataclass
class YahooDailyCache:
    """
    Tiny cache: one file per ticker per day, storing the OHLCV dataframe
    yfinance returns for that ticker for the requested start/end.

    Location: data/market/cache/
    """
    cache_dir: Path = Path("data/market/cache")

    def __post_init__(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def path(self, ticker: str, start: str, end: str, asof: Optional[str] = None) -> Path:
        asof = asof or _today_str()
        t = _safe_ticker(ticker)
        # Include date range so you don’t mix different pulls in the same day.
        s = start.replace("-", "")
        e = end.replace("-", "")
        return self.cache_dir / f"{t}__{asof}__{s}_{e}.parquet"

    def load(self, ticker: str, start: str, end: str, asof: Optional[str] = None) -> Optional[pd.DataFrame]:
        p = self.path(ticker, start, end, asof=asof)
        if not p.exists():
            return None
        try:
            df = pd.read_parquet(p)
            # Ensure DatetimeIndex
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"])
                df = df.set_index("Date")
            else:
                if not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            return df
        except Exception:
            return None

    def save(self, ticker: str, start: str, end: str, df: pd.DataFrame, asof: Optional[str] = None) -> None:
        p = self.path(ticker, start, end, asof=asof)
        out = df.copy()
        # Make parquet robust if index name is missing
        if out.index.name is None:
            out.index.name = "Date"
        out.to_parquet(p, index=True)
