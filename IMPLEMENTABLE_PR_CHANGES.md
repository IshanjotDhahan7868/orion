# Implementable PR Changes (Agent-Executable)

This is a concrete list of PRs I can implement directly in this repository, in sequence.

## PR 1 — Build a real pipeline orchestrator (`scripts/run_all.py`)

### Scope
- Replace placeholder `scripts/run_all.py` with an executable orchestrator.
- Add ordered stage execution for:
  1. Week 4 event dry run
  2. Week 5 propagation/scoring
  3. Week 6 market check
  4. Week 7 signal export
- Add CLI flags:
  - `--from-week` and `--to-week`
  - `--stop-on-error` (default true)
  - `--print-commands`

### Acceptance criteria
- `python scripts/run_all.py` runs a full local pipeline with clear logs.
- Outputs are generated in `data/processed/` (including `signals_week6.csv`, `signals_v1_2.json`, and `weekly_brief.md`) when prerequisites are available.
- Non-zero exit code on failed stage with readable error context.

---

## PR 2 — Fix ingestion price fetcher reliability (`ingestion/fetchers/fetch_asset_prices.py`)

### Scope
- Fix function ordering bug where `get_all_tickers_from_graph` is used before definition.
- Move DB credentials to environment variables with safe fallback messaging.
- Harden yfinance row parsing to avoid scalar/index ambiguity.
- Add small guardrails for empty downloads.

### Acceptance criteria
- Script imports without `NameError`.
- Running the fetcher does not crash on empty ticker responses.
- DB connection config no longer requires hardcoded password in source code.

---

## PR 3 — Implement ingestion tests (`tests/test_ingestion.py`)

### Scope
- Replace placeholder with real tests for:
  - entity extraction hit/miss behavior
  - event builder confidence gate (`None` when below threshold)
  - noise filter behavior on known noisy phrases
- Use deterministic fixtures/text snippets (no network dependencies).

### Acceptance criteria
- `pytest -q` includes ingestion tests and passes locally.
- Tests validate core Week 4 logic correctness in a regression-safe way.

---

## PR 4 — Implement scoring tests (`tests/test_scoring.py`)

### Scope
- Replace placeholder with tests for `market.filters.confirm_and_rescore`:
  - confirmation score calculation
  - risk penalty composition
  - adjusted score formula
  - NaN/missing-column safety

### Acceptance criteria
- `pytest -q` includes scoring tests and passes locally.
- Formula behavior is validated with controlled pandas fixtures.

---

## PR 5 — Add minimal signal viewer UI (`ui/app.py`)

### Scope
- Replace placeholder with a minimal Streamlit app (or Flask fallback) that:
  - loads `data/processed/signals_v1_2.json`
  - shows sortable top signals table
  - renders per-signal explanation, market checks, and risk flags
- Add a short run instruction block at top of file.

### Acceptance criteria
- App launches locally and displays generated signal artifacts.
- Missing file states are handled with user-friendly messages.

---

## PR 6 — Add execution MVP: position sizing (`execution/position_sizing.py`)

### Scope
- Replace placeholder with pure functions for:
  - converting normalized signal scores to target weights
  - applying caps (`max_per_asset`, `max_per_theme`)
  - re-normalizing portfolio weights
- Include docstring examples.

### Acceptance criteria
- Position sizing functions are deterministic and unit-testable.
- Outputs always sum to <= 1.0 and respect configured caps.

---

## PR 7 — Add backtest MVP (`evolution/backtest.py`)

### Scope
- Replace placeholder with event-replay utilities:
  - load historical signal CSV/JSON
  - simulate fixed holding window returns using available market data
  - output summary metrics (hit rate, avg return, drawdown proxy)

### Acceptance criteria
- Backtest module can run offline on local artifacts.
- Produces a structured summary dict (and optional CSV report).

---

## PR 8 — Add lightweight learning loop scaffold (`evolution/learning.py`)

### Scope
- Replace placeholder with helpers to:
  - compare predicted strength vs realized move buckets
  - suggest edge-weight adjustment candidates (non-destructive)
  - emit recommendation report (no auto-write to graph by default)

### Acceptance criteria
- Learning module returns interpretable recommendation objects.
- No direct mutation of production graph unless explicitly enabled.

---

## PR 9 — Documentation + runbook polish

### Scope
- Add a concise runbook section to `README.md`:
  - one-command run
  - stage-by-stage run
  - expected artifacts
  - common failure modes
- Add section describing current limitations and next planned enhancements.

### Acceptance criteria
- New contributor can run the pipeline from docs without reading source code first.
- README reflects the actual script/module behavior after PRs 1–8.

---

## Suggested merge order
1. PR 1 (orchestrator)
2. PR 2 (price fetcher reliability)
3. PR 3 + PR 4 (test coverage)
4. PR 5 (UI)
5. PR 6 + PR 7 + PR 8 (execution/evolution MVPs)
6. PR 9 (docs polish)

## Notes
- I can implement all PRs above directly in this repo without external service dependencies beyond existing Python packages and optional market data pulls.
- For UI PRs, I can also provide screenshot artifacts if a runnable frontend route is available.
