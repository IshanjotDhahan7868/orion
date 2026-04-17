from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from api.service import (
    build_portfolio_recommendation,
    create_portfolio_snapshot,
    generate_daily_brief,
    get_graph_node,
    get_latest_brief,
    get_latest_portfolio_snapshot,
    get_watchlists,
    list_recent_events,
    list_signals,
    refresh_intelligence_state,
    run_what_if,
    set_watchlist,
)


class EventRequest(BaseModel):
    text: str = Field(..., min_length=5, description="News headline or event description.")
    dry_run: bool = True
    top_n: int = Field(default=10, ge=1, le=50)


class PortfolioRequest(BaseModel):
    limit: int = Field(default=12, ge=1, le=50)
    min_score: float = Field(default=0.0, ge=0.0)
    gross_exposure: float = Field(default=1.0, ge=0.0, le=1.0)
    max_per_asset: float = Field(default=0.10, ge=0.01, le=1.0)
    max_per_theme: float = Field(default=0.30, ge=0.01, le=1.0)
    confirmed_only: bool = True


class WatchlistRequest(BaseModel):
    name: str = Field(default="core", min_length=1, max_length=64)
    assets: list[str] = Field(default_factory=list)
    notes: str = ""


class BriefRequest(BaseModel):
    watchlist_name: str = Field(default="core", min_length=1, max_length=64)
    use_ai: bool = True


app = FastAPI(
    title="ORION Engine",
    version="0.1.0",
    description="Causal macro intelligence engine for signals, events, graph lookups, and what-if scenarios.",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "orion-engine"}


@app.post("/api/bootstrap/refresh")
def api_bootstrap_refresh() -> dict:
    return refresh_intelligence_state()


@app.get("/api/signals")
def api_signals(limit: int = 50) -> dict:
    limit = max(1, min(limit, 200))
    signals = list_signals(limit=limit)
    return {"signals": signals, "count": len(signals)}


@app.get("/api/events")
def api_events(limit: int = 20) -> dict:
    limit = max(1, min(limit, 100))
    events = list_recent_events(limit=limit)
    return {"events": events, "count": len(events)}


@app.get("/api/graph/node/{node_id}")
def api_graph_node(node_id: str) -> dict:
    node = get_graph_node(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f'Node "{node_id}" not found')
    return node


@app.post("/api/event")
def api_event(payload: EventRequest) -> dict:
    return run_what_if(payload.text, dry_run=payload.dry_run, top_n=payload.top_n)


@app.post("/api/portfolio/recommendation")
def api_portfolio_recommendation(payload: PortfolioRequest) -> dict:
    return build_portfolio_recommendation(
        limit=payload.limit,
        min_score=payload.min_score,
        gross_exposure=payload.gross_exposure,
        max_per_asset=payload.max_per_asset,
        max_per_theme=payload.max_per_theme,
        confirmed_only=payload.confirmed_only,
    )


@app.post("/api/portfolio/snapshot")
def api_portfolio_snapshot(payload: PortfolioRequest) -> dict:
    return create_portfolio_snapshot(
        limit=payload.limit,
        min_score=payload.min_score,
        gross_exposure=payload.gross_exposure,
        max_per_asset=payload.max_per_asset,
        max_per_theme=payload.max_per_theme,
        confirmed_only=payload.confirmed_only,
    )


@app.get("/api/portfolio/latest")
def api_portfolio_latest() -> dict:
    snapshot = get_latest_portfolio_snapshot()
    if snapshot is None:
        raise HTTPException(status_code=404, detail="No portfolio snapshot found")
    return snapshot


@app.get("/api/watchlists")
def api_watchlists() -> dict:
    watchlists = get_watchlists()
    return {"watchlists": watchlists, "count": len(watchlists)}


@app.post("/api/watchlists")
def api_watchlists_upsert(payload: WatchlistRequest) -> dict:
    return set_watchlist(name=payload.name, assets=payload.assets, notes=payload.notes)


@app.get("/api/briefs/latest")
def api_briefs_latest() -> dict:
    brief = get_latest_brief()
    if brief is None:
        raise HTTPException(status_code=404, detail="No analyst brief found")
    return brief


@app.post("/api/briefs/generate")
def api_briefs_generate(payload: BriefRequest) -> dict:
    return generate_daily_brief(watchlist_name=payload.watchlist_name, use_ai=payload.use_ai)
