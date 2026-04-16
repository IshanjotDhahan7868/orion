"""Tests for market confirmation and rescoring formulas."""

import math

import pandas as pd

from market.filters import confirm_and_rescore


def test_confirm_and_rescore_formula_and_penalty():
    signals = pd.DataFrame(
        [
            {
                "asset": "XLE",
                "score_norm": 0.8,
                "why_path": "Trade_Restrictions -> Oil_and_Gas",
            }
        ]
    )
    market = pd.DataFrame(
        [
            {
                "asset": "XLE",
                "rs_1m": 0.05,
                "rs_3m": 0.01,
                "above_ma50": 1,
                "golden": 1,
                "vol_z20": 0.2,
            }
        ]
    )
    assets_meta = {"XLE": {"type": "etf"}}

    out, flags = confirm_and_rescore(signals, market, assets_meta)

    assert out.loc[0, "confirm_score"] == 1.0
    assert math.isclose(out.loc[0, "penalty"], 0.35)  # regulatory + cyclical + crowded
    expected = 0.8 * (1 + 0.25 * 1.0) * (1 - 0.2 * 0.35)
    assert math.isclose(out.loc[0, "adj_score"], expected, rel_tol=1e-9)

    assert flags[0]["regulatory"] is True
    assert flags[0]["cyclical"] is True
    assert flags[0]["crowded"] is True


def test_confirm_and_rescore_handles_missing_market_columns():
    signals = pd.DataFrame(
        [{"asset": "AAPL", "score_norm": 0.5, "why_path": "Innovation"}]
    )
    market = pd.DataFrame([{"asset": "AAPL"}])

    out, _ = confirm_and_rescore(signals, market, assets_meta={"AAPL": {"type": "equity"}})

    assert out.loc[0, "confirm_score"] == 0.0
    assert out.loc[0, "penalty"] == 0.0
    assert out.loc[0, "adj_score"] == 0.5
