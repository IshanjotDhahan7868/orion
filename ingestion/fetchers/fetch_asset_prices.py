from __future__ import annotations

import os
from pathlib import Path

import psycopg2
import yfinance as yf
import yaml

BASE_DIR = Path(__file__).resolve().parents[2]
GRAPH_PATH = BASE_DIR / "config" / "graph.yaml"


DEFAULT_DB_CONN = {
    "host": os.getenv("ORION_DB_HOST", "localhost"),
    "dbname": os.getenv("ORION_DB_NAME", "orion"),
    "user": os.getenv("ORION_DB_USER", "postgres"),
    "password": os.getenv("ORION_DB_PASSWORD", ""),
    "port": int(os.getenv("ORION_DB_PORT", "5432")),
}


def get_all_tickers_from_graph(graph_path: str | Path) -> list[str]:
    """Load unique tickers from graph node assets."""
    with open(graph_path, "r", encoding="utf-8") as f:
        graph = yaml.safe_load(f) or {}

    tickers: set[str] = set()
    for node in graph.get("nodes", []):
        assets = node.get("assets", {}) or {}
        for key in ("equities", "etfs", "commodities"):
            for ticker in assets.get(key, []) or []:
                if isinstance(ticker, str) and ticker.strip():
                    tickers.add(ticker.strip())
    return sorted(tickers)


TICKERS = get_all_tickers_from_graph(GRAPH_PATH)


def get_db_conn(conn_info: dict | None = None):
    conn_cfg = dict(DEFAULT_DB_CONN)
    if conn_info:
        conn_cfg.update(conn_info)

    if not conn_cfg.get("password"):
        print("ORION_DB_PASSWORD is not set; attempting DB connection without a password.")

    return psycopg2.connect(**conn_cfg)


def _safe_float(v):
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def _safe_int(v):
    if v is None:
        return None
    try:
        return int(v)
    except Exception:
        return None


def fetch_and_store_prices(tickers: list[str] | None = None, conn_info: dict | None = None) -> None:
    tickers = tickers or TICKERS
    if not tickers:
        print("No tickers found in graph config; nothing to fetch.")
        return

    with get_db_conn(conn_info) as conn, conn.cursor() as cur:
        for ticker in tickers:
            print(f"Fetching {ticker}...")
            try:
                data = yf.download(ticker, period="2y", interval="1d", progress=False)
                if data is None or data.empty:
                    print(f"No data returned for {ticker}; skipping.")
                    continue

                inserted = 0
                for date, row in data.iterrows():
                    close = _safe_float(row.get("Close"))
                    volume = _safe_int(row.get("Volume"))
                    if close is None:
                        continue

                    cur.execute(
                        """
                        INSERT INTO asset_prices (ticker, price_date, close, volume)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (ticker, price_date) DO NOTHING
                        """,
                        (ticker, date.date(), close, volume),
                    )
                    inserted += 1

                print(f"Stored {inserted} rows for {ticker}")
            except Exception as exc:
                print(f"Failed to fetch/store {ticker}: {exc}")

        conn.commit()
    print("Done fetching price history.")


if __name__ == "__main__":
    fetch_and_store_prices()
