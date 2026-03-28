# Approach

## Purpose

This project exists to make speciesist-bias evaluation repeatable and auditable for language models used in advocacy contexts.

## Current State (Implemented)

The active implementation is in the repository root and follows a modular architecture:

1. Prompt templates: Jinja2 files in `templates/`.
2. Runner: `benchmark/runner.py` orchestrates rendering, model calls, scoring, and persistence.
3. API client: `benchmark/openrouter_client.py` handles OpenRouter requests, retries, and normalization.
4. Scorer: `benchmark/scorer.py` performs deterministic rubric-based scoring.
5. Storage: SQLite with SQLAlchemy models in `database/models.py` and transactional helpers in `database/db.py`.
6. Reporting: `benchmark/report_generator.py` writes static HTML reports to `reports/`.
7. Dashboard: `app.py` and `dashboard/` read SQLite only and never call OpenRouter directly.

## Design Decisions

### Deterministic scoring over judge-model scoring

Scoring is intentionally rule-based so results remain explainable and cheap to run.

### SQLite as source of truth

All benchmark results (runs, prompts, responses, scores, model metadata) are persisted in SQLite for reproducibility.

### Headless-capable benchmark execution

The CLI can run in automation contexts without Streamlit.

### Read-only analytics UI

The dashboard is a viewer over persisted benchmark data, not an execution layer.

## Current Run Flow

1. `run_benchmark.py` parses args and loads settings from `.env` via `config.py`.
2. Runner renders prompt templates and executes model calls through OpenRouter.
3. Responses are scored deterministically and persisted transactionally.
4. Optional HTML report export writes files to `reports/`.
5. `app.py` reads persisted runs from SQLite for filtering and analysis.

## Constraints Enforced in Code

1. No hardcoded secrets.
2. Transactional writes for benchmark persistence.
3. Dashboard never performs model API calls.
4. Environment-based configuration via `.env`.
5. Test coverage for scorer, templates, DB behavior, and client normalization/retries.

## Future Work (Not Yet Implemented)

1. Additional benchmark dimensions beyond the current three.
2. Human review workflow for low-confidence or contested cases.
3. Run-to-run drift analysis views in dashboard/reporting.
4. Optional secondary judge-model analysis as a non-default add-on.
