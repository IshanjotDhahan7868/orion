from api.service import (
    build_portfolio_recommendation,
    create_portfolio_snapshot,
    generate_daily_brief,
    get_graph_node,
    refresh_intelligence_state,
    run_what_if,
    set_watchlist,
)


def test_get_graph_node_returns_metadata():
    node = get_graph_node("AI_Compute_Demand")

    assert node is not None
    assert node["id"] == "AI_Compute_Demand"
    assert node["theme"]


def test_run_what_if_returns_ranked_signals():
    result = run_what_if("TSMC plans a major new advanced chip fab expansion in Arizona.")

    assert result["events"]
    assert result["signals"]
    assert result["events"][0]["seeded_nodes"]
    assert result["signals"][0]["asset"]
    assert result["signals"][0]["score"] >= result["signals"][-1]["score"]


def test_build_portfolio_recommendation_respects_caps():
    result = build_portfolio_recommendation(limit=8, max_per_asset=0.12, max_per_theme=0.3)

    assert result["positions"]
    assert result["summary"]["gross_exposure"] <= 1.0
    assert all(position["weight"] <= 0.12 for position in result["positions"])


def test_refresh_watchlist_snapshot_and_brief_flow():
    refresh = refresh_intelligence_state()
    assert refresh["ontology_entities"] > 0

    watchlist = set_watchlist("test", ["NVDA", "TSM", "ASML"], notes="core semis")
    assert "NVDA" in watchlist["assets"]

    snapshot = create_portfolio_snapshot(label="Test Snapshot", limit=6)
    assert snapshot["positions"]

    brief = generate_daily_brief(watchlist_name="test", use_ai=False)
    assert "Regime" in brief["body"]
    assert brief["metadata"]["watchlist_name"] == "test"
