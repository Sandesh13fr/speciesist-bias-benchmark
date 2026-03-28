# Speciesist Bias Benchmark

Production-oriented benchmark for measuring speciesist bias in LLM responses.

The repository root is the active application.

## How It Works

1. The CLI in `run_benchmark.py` runs benchmark cases headlessly across selected models.
2. Prompts are rendered from Jinja2 templates in `templates/`.
3. Responses and deterministic scores are written transactionally to SQLite.
4. HTML reports are generated from persisted benchmark data in `reports/`.
5. The Streamlit dashboard in `app.py` reads SQLite only and visualizes results.

## Architecture

```text
run_benchmark.py (CLI)
  -> config.py + logging_config.py
  -> benchmark/runner.py
      -> templates/*.j2 (Jinja2 rendering)
      -> benchmark/openrouter_client.py (OpenRouter calls)
      -> benchmark/scorer.py (deterministic scoring)
      -> database/models.py + database/db.py (SQLite persistence)
      -> benchmark/report_generator.py (static HTML report)

app.py (Streamlit)
  -> dashboard/components.py + dashboard/pages/*
  -> SQLite reads only (no model API calls)
```

## Repository Structure

```text
OpenPaws_Assesment/
|-- .env.example
|-- .gitignore
|-- README.md
|-- APPROACH.md
|-- requirements.txt
|-- Dockerfile
|-- docker-compose.yml
|-- config.py
|-- logging_config.py
|-- run_benchmark.py
|-- app.py
|-- benchmark/
|   |-- runner.py
|   |-- scorer.py
|   |-- openrouter_client.py
|   |-- report_generator.py
|   `-- templates_engine.py
|-- database/
|   |-- models.py
|   |-- db.py
|   `-- repository.py
|-- dashboard/
|   |-- components.py
|   |-- data_access.py
|   `-- pages/
|       |-- overview.py
|       |-- model_detail.py
|       `-- raw_results.py
|-- templates/
|   |-- euphemism.j2
|   |-- food_defaults.j2
|   `-- framing_neutrality.j2
|-- docs/
|   |-- API_COST_ESTIMATION.md
|   |-- DELIVERABLE_INDEX.md
|   |-- EXTENDING.md
|   |-- OPENROUTER_SETUP.md
|   |-- SCOPE_GUIDE.md
|   |-- ai_builder_prompts.md
|   |-- diagram_prompts.md
|   |-- research_document.md
|   |-- sample_results.md
|   `-- scoring_rubric.md
|-- tests/
|   |-- test_scorer.py
|   |-- test_templates.py
|   |-- test_db.py
|   `-- test_client.py
`-- reports/ (generated)
```

## Setup

### 1. Create and activate virtual environment

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and set at least:

```env
OPENROUTER_API_KEY=your_key_here
DEFAULT_MODELS=openai/gpt-4o-mini,openai/gpt-4o,anthropic/claude-3-haiku
DATABASE_URL=sqlite:///speciesist_bias.db
```

Secrets are loaded through `config.py` and must never be hardcoded.

### 4. SQLite bootstrap (first run)

The SQLite file is intentionally not committed.

On the first real benchmark run, the app automatically:

1. creates the SQLite database file (default: `speciesist_bias.db`), and
2. initializes required tables via SQLAlchemy.

Run this once to bootstrap data storage:

```powershell
python run_benchmark.py --models openai/gpt-4o-mini --export html --run-label first-run
```

If you open Streamlit before any benchmark run, the dashboard will show that no runs are available yet.

## Running the Benchmark

### List configured models

```powershell
python run_benchmark.py --list-models
```

### Dry run (no OpenRouter calls)

```powershell
python run_benchmark.py --models all --dry-run --max-prompts-per-dimension 1
```

### Full run with report export

```powershell
python run_benchmark.py --models all --export html --run-label baseline-run
```

## Running the Dashboard

```powershell
streamlit run app.py
```

The dashboard is intentionally read-only and only queries SQLite data. It does not call OpenRouter.

## Reports

- HTML reports are generated into `reports/`.
- `reports/latest.html` is updated on each exported run.

## Testing and Quality Checks

```powershell
ruff check .
pytest -q
```

## Docker

Container support is available via `Dockerfile` and `docker-compose.yml`.

```powershell
docker compose run --rm benchmark
docker compose up dashboard
```

Both services share a mounted SQLite volume for persistence.

## CI

GitHub Actions workflow exists at `.github/workflows/ci.yml` and runs lint, tests, and template validation on push and pull requests.
