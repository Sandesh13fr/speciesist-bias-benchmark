# Scope and Development Standards

This document defines the current engineering constraints for the active root project.

## Current Architecture Contract

1. CLI benchmark execution in `run_benchmark.py`.
2. Read-only Streamlit dashboard in `app.py`.
3. Jinja2 prompt templates in `templates/`.
4. Deterministic scoring in `benchmark/scorer.py`.
5. Transactional SQLite persistence via `database/`.
6. HTML report generation in `benchmark/report_generator.py`.

## Non-Negotiable Rules

1. No hardcoded secrets.
2. OpenRouter credentials must come from environment variables.
3. Dashboard must never call model APIs.
4. All benchmark writes must be transactional.
5. Public functions should remain typed and documented.
6. Production code should use logging over print.

## Runtime Data Flow

1. CLI parses args and loads settings from `.env`.
2. Runner renders templates and calls OpenRouter through client abstraction.
3. Responses are scored deterministically and persisted to SQLite.
4. Report generation reads persisted data and writes standalone HTML.
5. Streamlit reads the same SQLite data for analysis.

## Repository Layout (Current)

```text
OpenPaws_Assesment/
|-- run_benchmark.py
|-- app.py
|-- config.py
|-- logging_config.py
|-- benchmark/
|-- database/
|-- dashboard/
|-- templates/
|-- tests/
|-- docs/
|-- Dockerfile
|-- docker-compose.yml
`-- .github/workflows/ci.yml
```

## Quality Gates Before Push

1. `ruff check .`
2. `pytest -q`
3. `python run_benchmark.py --help`
4. `python run_benchmark.py --list-models`
5. Template rendering validation (covered in CI)

## Current vs Future

Current:

1. Headless benchmark execution works.
2. SQLite-backed report and dashboard workflow is implemented.

Future:

1. Additional dimensions and analytics pages.
2. Optional advanced evaluation workflows.
