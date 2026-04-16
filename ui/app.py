"""ORION signal viewer.

Run:
    streamlit run ui/app.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1]
SIGNALS_PATH = BASE_DIR / "data" / "processed" / "signals_v1_2.json"


@st.cache_data
def load_signals(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, dict) and "signals" in payload:
        return payload["signals"]
    if isinstance(payload, list):
        return payload
    return []


def main() -> None:
    st.set_page_config(page_title="ORION Signals", layout="wide")
    st.title("ORION Signals Dashboard")

    if not SIGNALS_PATH.exists():
        st.warning(f"No signals file found at: {SIGNALS_PATH}")
        st.info("Run pipeline first: python scripts/run_all.py")
        return

    signals = load_signals(SIGNALS_PATH)
    if not signals:
        st.warning("Signals file loaded, but no signals were found.")
        return

    df = pd.DataFrame(signals)
    sort_col = "adj_score" if "adj_score" in df.columns else "score_norm"
    df = df.sort_values(sort_col, ascending=False).reset_index(drop=True)

    st.subheader("Top signals")
    st.dataframe(df, use_container_width=True)

    options = [f"{row.asset} ({row.symbol})" for row in df.itertuples(index=False)]
    selected = st.selectbox("Inspect signal", options)
    selected_idx = options.index(selected)
    row = df.iloc[selected_idx]

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Signal explanation")
        st.write({
            "asset": row.get("asset"),
            "symbol": row.get("symbol"),
            "why_path": row.get("why_path"),
            "when_months": row.get("when_months"),
            "score_norm": row.get("score_norm"),
            "adj_score": row.get("adj_score"),
        })

    with c2:
        st.markdown("### Market + risk")
        st.write({
            "market_status": row.get("market_status"),
            "reason": row.get("reason"),
            "confirmation_features": row.get("confirmation_features"),
            "risk_flags": row.get("risk_flags"),
        })


if __name__ == "__main__":
    main()
