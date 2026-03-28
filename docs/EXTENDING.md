# Extending the Benchmark

This guide covers extension work for the current root architecture.

## Current State Boundaries

1. Execution entry point: `run_benchmark.py`.
2. UI entry point: `app.py`.
3. SQLite is the source of truth.
4. Dashboard is read-only.
5. Templates are Jinja2 files under `templates/`.

## Add a New Dimension

1. Add a new template under `templates/`.
2. Add prompt cases in `benchmark/runner.py` (`default_prompt_cases`).
3. Add deterministic scoring logic in `benchmark/scorer.py`.
4. Update dimension dispatch in scorer and any reporting summaries.
5. Add tests in `tests/test_scorer.py` and `tests/test_templates.py`.
6. Update docs (`README.md`, `docs/SCORING_RUBRIC.md`, `docs/sample_results.md`).

## Add a New Model

1. Confirm model ID via OpenRouter.
2. Add to `DEFAULT_MODELS` in `.env`, or pass via CLI `--models`.
3. Run a small benchmark first:

```powershell
python run_benchmark.py --models your/model-id --max-prompts-per-dimension 1 --export html
```

4. Verify model appears in SQLite-backed dashboard and report output.

## Modify Scoring

When changing scoring behavior:

1. Update deterministic logic in `benchmark/scorer.py`.
2. Keep score range normalized to 0-10.
3. Maintain machine-readable breakdown fields.
4. Add regression tests for high, low, and edge cases.
5. Update `docs/SCORING_RUBRIC.md`.

## Extend the Dashboard

1. Add new reusable rendering helpers in `dashboard/components.py`.
2. Add new page under `dashboard/pages/`.
3. Wire route selection in `app.py`.
4. Keep dashboard strictly read-only over SQLite.

## Extend Reports

`benchmark/report_generator.py` is the reporting source.

Rules:

1. Generate standalone HTML.
2. Read from SQLite data only.
3. Do not trigger model calls during report generation.

## Future Work Ideas (Not Implemented)

1. Additional dimensions.
2. Human adjudication workflow.
3. Run-to-run drift comparison views.
4. Optional advanced budget/cost summaries from usage metadata.
