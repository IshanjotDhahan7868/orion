ORION Macro-Signal Investing System

Permanent Project Instructions

Project Description

ORION is a macro-signal investing system designed to detect, model, and act on regime shifts and major world events across technology, economics, energy, and geopolitics. It is built to be causal, explainable, and time-aware, never relying on black-box models or simple price prediction.
The system is engineered around a multi-phase pipeline:

PHASE 0 — Foundations:
Define ORION’s mental model, key concepts, and what the system will—and will not—do. Set core taxonomies (themes, event types, causality, lags).

PHASE 1 — ORION Graph:
Construct an explicit, version-controlled dependency graph that encodes real-world cause and effect, mapping events to downstream impacts and ultimately to assets (public equities, ETFs, commodities).

PHASE 2 — World Intake Layer:
Build robust, auditable pipelines to ingest and normalize global news, releases, macro data, and policy changes, storing raw information for later replay or audit.

PHASE 3 — Event Intelligence Engine:
Extract, classify, and score meaningful events from raw data using rule-based or hybrid methods. Suppress noise and map events to nodes in the graph.

PHASE 4 — Propagation & Impact Modeling:
Propagate structured events through the graph, surfacing second- and third-order effects. Aggregate impacts and explain “why this asset, now.”

PHASE 5 — Market Reality Filter:
Confirm signals against market data (price, volume, relative strength, risk factors) to filter out “storytelling” and ground everything in reality.

PHASE 6 — ORION Signals:
Generate and deliver actionable, human-readable signals, complete with explainability trails and risk context.

PHASE 7 — Execution Layer (Optional):
Only after signal trust is earned, automate capital movement (manual, semi-auto, auto) with strict sizing and allocation rules.

PHASE 8 — Evolution & Scale:
Enable feedback, learning, backtesting, and auditability so ORION gets smarter and more robust over time.

What Makes ORION Different:

It never predicts price directly

All outputs are causal, explainable, and time-aware

No black-box logic or day trading

Designed for decades of durability

All work maps to explicit project phases and a clear directory structure

Timeline & Weekly Checklist

WEEK 1: Foundations & Mental Model Lock

Goal: Lock what ORION is, how it thinks, and why—to prevent confusion later.

Checklist:

Write a 1-page doc: “ORION: What it is, what it’s not”

List core themes (AI, Energy, Defense, etc.) with definitions

List event types (CapEx, supply, etc.) with 1-line examples

Define first/second/third-order effects (with real-world examples)

Define “lag” (timing between event/effect) with scenarios

List 5 things ORION won’t do (e.g., no day trading, no black-box AI magic)

End-of-week: Reflect—can you explain ORION to a friend in 2 minutes?

WEEK 2: Build the ORION Graph (Dependency Map)

Goal: Draft and formalize the dependency graph (cause/effect map).

Checklist:

List all nodes (drivers, industries, sub-industries, commodities) per theme

For each node, write “What is this?” and “What affects it?”

Draw edges/arrows, specifying effect strength/lag

Assign weights (0.1 = weak, 1.0 = very strong) and lag (immediate, months, years)

Mark asset mapping (public companies, ETFs, commodities)

Represent graph in YAML or JSON (from: A, to: B, weight: 0.8, lag: 'months')

Walk through 2–3 historical events in your graph—does it make sense?

Version the graph (v1.0)

WEEK 3: Data Intake & Raw Storage Setup

Goal: Set up a minimal, working data ingestion and storage pipeline.

Checklist:

Choose news/press release sources (RSS feeds, company IR, macro sites)

Write scripts to fetch and store text + metadata

Set up Postgres/Supabase with tables: raw_items, events, graph_nodes, graph_edges, tickers

Store and index every raw story (immutable, timestamp/source/URL)

Deduplicate incoming stories

Ensure retrieval of any old event by date/source

(Optional) Add one financial data feed (e.g., Yahoo Finance for EOD prices)

WEEK 4: Event Intelligence Engine v1

Goal: Turn news text into structured, actionable events.

Checklist:

Write keyword/rule-based extractors (companies, event types, tech, commodities)

Tag each story: main company/asset, event type, confidence (1–10)

Filter out noise (earnings dates, generic interviews, price-only news)

Output “event” objects to DB: headline, date, type, entities, affected nodes

Review 20–50 events by hand, tweak rules as needed

Add lag estimation per event

Test by injecting real historical events

Weekly review: Are you surfacing actionable changes or too much noise?

WEEK 5: Graph Propagation & Impact Modeling

Goal: Get events to flow through the dependency graph and produce ranked lists of affected assets.

Checklist:

Inject events at correct graph node(s)

Write propagation logic (decay by weight/distance/lag)

Aggregate signals that reach each asset

Implement simple scoring; show top 10 affected assets per event

Explain: “This is ranked high because…” (event → asset explanation trail)

Validate with historical events—do non-obvious winners surface?

Document propagation failures/odd results for v2

WEEK 6: Market Reality Check

Goal: Connect your system to market data—don’t get tricked by stories.

Checklist:

For each asset, fetch price, volume, benchmark (SPY, QQQ)

Add filters: outperforming market? volume up? uptrend?

Add “risk flags”: overvalued, crowded, regulatory, cyclicality

Refine scoring; penalize assets failing reality, boost with confirmation

Output: signals show “why” and “is it actually moving?”

Test: Compare ranked list to recent real events

WEEK 7: ORION Signals — Human-Readable Output

Goal: Produce clear, trustworthy output—signals you’d actually use.

Checklist:

For each high-scoring asset, generate a human-readable signal object (asset, theme, event, why, score, risk, time window)

Build minimal UI/report (Markdown, Notion, web page)

(Optional) Set up automated alerts (email, Discord, etc.)

Test: Read a week of signals—do you trust them? Are they “obvious in hindsight”?

Make a checklist of what to improve next

WEEK 8: (Optional/Advanced) Execution Layer & Evolution

Goal: Prepare for automation and future-proofing.

Checklist:

Define position sizing rules (“never more than X% per theme”)

Add logic for manual/semi-auto/auto signal execution (mock trades, paper trading, etc.)

Enable feedback/learning loop (review what worked/failed)

Set up logs for every action (“audit trail”)

Brainstorm v2/v3: graph learning, backtesting, SaaS scaling

Directory Structure
orion/
    README.md
    requirements.txt
    .env
    .gitignore
    config/
        settings.yaml
        graph.yaml
        tickers.yaml
    data/
        raw/
        processed/
        market/
        backtests/
        examples/
    db/
        migrations/
        models.py
        seed_data.py
    ingestion/
        fetchers/
            rss_fetcher.py
            pr_fetcher.py
            macro_fetcher.py
        __init__.py
    processing/
        entity_extraction.py
        event_classifier.py
        noise_filter.py
        __init__.py
    graph/
        dependency_graph.py
        propagate.py
        visualize.py
    scoring/
        score_engine.py
        market_filter.py
        risk_flags.py
    signals/
        signal_generator.py
        explain.py
        delivery.py
    execution/
        position_sizing.py
        trade_simulator.py
        auto_execute.py
    evolution/
        learning.py
        backtest.py
    tests/
        test_graph.py
        test_ingestion.py
        test_scoring.py
    scripts/
        run_all.py
        seed_graph.py
        export_signals.py
    notebooks/
        orion_demo.ipynb
        graph_analysis.ipynb
        market_analysis.ipynb
    ui/
        app.py
        components/
        static/
## Quick Runbook (Current Implementation)

### One-command run

```bash
python scripts/run_all.py
```

### Stage-by-stage run

```bash
python scripts/week4_dry_run.py
python scripts/week5_dry_run.py
python scripts/week6_market_check.py
python scripts/week7_export_signals.py
```

### Orchestrator options

```bash
python scripts/run_all.py --from-week 5 --to-week 7 --print-commands
python scripts/run_all.py --from-week 4 --to-week 7 --no-stop-on-error
```

### Expected artifacts

- `data/processed/signals.csv` (Week 5)
- `data/processed/signals_week6.csv` (Week 6 market-checked)
- `data/processed/signals_v1_2.json` (Week 7 exported signals)
- `data/processed/weekly_brief.md` (Week 7 brief)

### Common failure modes

- **Missing Week 5 output:** Week 6 exits if `signals.csv` does not exist.
- **No market mapping:** assets without a symbol mapping are marked as skipped/missing and softly penalized.
- **No DB password for price ingestion:** `ORION_DB_PASSWORD` defaults to empty; set env vars before loading price history into Postgres.

### Current limitations and next enhancements

- Event extraction/classification is still rule-based and should be expanded with richer patterns.
- Risk flag logic is intentionally conservative and can be made theme-aware.
- Backtest/learning modules are scaffold-level and meant for offline artifact iteration before production automation.
