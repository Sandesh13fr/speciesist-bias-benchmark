# Diagram Prompts

Use these prompts to generate diagrams that match the current implementation.

## 1. High-Level Architecture

Prompt:

Create a system architecture diagram for the current root project.

Include:

1. `run_benchmark.py` (CLI)
2. `app.py` (Streamlit)
3. `config.py` and `logging_config.py`
4. `benchmark/runner.py`
5. `benchmark/openrouter_client.py`
6. `benchmark/scorer.py`
7. `database/db.py` + `database/models.py`
8. `benchmark/report_generator.py`
9. `templates/*.j2`
10. `reports/`
11. `dashboard/components.py` + `dashboard/pages/*`

Rules to show:

1. CLI runs benchmark execution.
2. Runner calls OpenRouter through client abstraction.
3. Results are persisted to SQLite.
4. Report generator reads persisted data and writes HTML.
5. Dashboard reads SQLite only and never calls OpenRouter.

## 2. ERD Prompt

Prompt:

Create an ER diagram from current SQLite/SQLAlchemy tables:

1. `runs`
2. `prompts`
3. `responses`
4. `scores`
5. `model_metadata`

Show one-to-many relationships and foreign keys.

## 3. Runner Flow Prompt

Prompt:

Generate a flowchart for benchmark execution:

1. Parse CLI args in `run_benchmark.py`.
2. Load settings from `.env` through `config.py`.
3. Initialize DB schema if needed.
4. Render Jinja2 templates.
5. Iterate models and prompt cases.
6. Call OpenRouter client with retry handling.
7. Persist responses and deterministic scores transactionally.
8. Mark run status (`completed`, `partial_failure`, or `failed`).
9. Optionally export HTML report.

## 4. Scoring Pipeline Prompt

Prompt:

Create an explainer diagram for deterministic scoring in `benchmark/scorer.py` covering:

1. Euphemism
2. Food defaults
3. Framing neutrality

Include refusal/malformed handling and composite score calculation.

## 5. Dashboard Wireframe Prompt

Prompt:

Design a wireframe for the current read-only Streamlit dashboard:

1. Sidebar filters: run selector, model filter, dimension filter, score range, failure toggle.
2. Routes: Overview, Model Detail, Raw Results.
3. Overview: KPI cards, model table, dimension chart, run metadata.
4. Model Detail: selected model summary, per-dimension breakdown, prompt table, failure diagnostics.
5. Raw Results: searchable table, response viewer, score breakdown preview.

State explicitly that the dashboard reads SQLite only.
