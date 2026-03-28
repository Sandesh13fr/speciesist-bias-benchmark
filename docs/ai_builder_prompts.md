# AI Builder Prompts

These prompts are aligned to the current root codebase.

## Prompt 1: Audit Existing Root State

```text
Audit the root project only.
List active runtime entry points, benchmark modules, database models, dashboard pages, tests, and docs.
Flag stale references and path mismatches.
```

## Prompt 2: Prompt Templates

```text
Implement or refine Jinja2 templates under templates/ for:
- euphemism
- food_defaults
- framing_neutrality
Keep rendering deterministic and validate missing-variable errors.
```

## Prompt 3: OpenRouter Client

```text
Implement benchmark/openrouter_client.py with:
- typed request/response normalization
- retries for transient failures
- non-retriable handling for 4xx
- model metadata listing support
- no hardcoded secrets
```

## Prompt 4: Deterministic Scorer

```text
Implement benchmark/scorer.py with deterministic scoring for:
- euphemism
- food_defaults
- framing_neutrality
Include refusal/malformed/truncated handling and composite score support.
```

## Prompt 5: Database Layer

```text
Implement SQLAlchemy + SQLite schema in database/models.py and database/db.py.
Ensure transactional writes and session rollback behavior.
Tables: runs, prompts, responses, scores, model_metadata.
```

## Prompt 6: Runner

```text
Implement benchmark/runner.py as orchestrator:
- render templates
- execute model calls
- score responses
- persist all artifacts transactionally
- continue on prompt-level failures
- summarize run outcomes
```

## Prompt 7: Streamlit Dashboard

```text
Implement read-only dashboard in app.py and dashboard/pages/*.
Dashboard must query SQLite only and never call OpenRouter.
Provide filters, overview, model detail, and raw results views.
```

## Prompt 8: HTML Reporting

```text
Implement benchmark/report_generator.py to generate standalone HTML reports from SQLite data.
Include leaderboard, dimension summary, failures, and appendix rows.
```

## Prompt 9: CLI

```text
Implement run_benchmark.py CLI with argparse:
- --models all or comma-separated list
- --dimensions
- --max-prompts-per-dimension
- --export html
- --run-label
- --list-models
- --dry-run
Help must work without API key.
```

## Prompt 10: Tests

```text
Implement deterministic pytest coverage for scorer, templates, DB, and OpenRouter client.
Mock network calls and use temporary SQLite for DB tests.
```

## Prompt 11: CI

```text
Implement .github/workflows/ci.yml with:
- push and pull_request triggers
- Python 3.11 on Ubuntu
- dependency install
- Ruff lint
- pytest
- template render validation
```

## Prompt 12: Containerization

```text
Implement Dockerfile and docker-compose.yml.
Default image command should launch Streamlit.
Compose must provide dashboard and benchmark services with persistent SQLite volume.
```

## Current vs Future

Current:

1. Prompts above map to already implemented architecture in this repository.
2. Use them mainly for maintenance or refactor work.

Future:

1. Add prompts for drift analysis and benchmark comparison workflows.
