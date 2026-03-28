# API Cost Estimation

This file estimates OpenRouter spend for the current benchmark implementation.

## Current State Assumptions

1. Three dimensions: euphemism, food_defaults, framing_neutrality.
2. Default prompt inventory: up to 5 cases per dimension.
3. Full run depth: 15 prompts per model.
4. Scoring is local and deterministic, so no extra judge-model cost.

## Token Planning Baseline

Use this planning formula per model:

```text
run_cost_per_model =
    (total_input_tokens / 1_000_000) * input_price_per_million
  + (total_output_tokens / 1_000_000) * output_price_per_million
```

Reference token budget for a full run (planning only):

1. Input tokens per model: 4,800
2. Output tokens per model: 2,600

## Practical Cost Strategy

1. Smoke test:
   - Use one cheap model.
   - Use `--max-prompts-per-dimension 1`.
2. Regression run:
   - Use several models.
   - Keep full prompt depth.
3. Submission run:
   - Use full model set with `--export html`.

## Current CLI Commands Used for Cost Control

```powershell
python run_benchmark.py --models all --dry-run --max-prompts-per-dimension 1
python run_benchmark.py --models openai/gpt-4o-mini --max-prompts-per-dimension 2
python run_benchmark.py --models all --export html --run-label full-comparison
```

## Current vs Future

Current state:

1. Cost is dominated by chosen model pricing and token volume.
2. Dashboard/report generation does not call OpenRouter and adds no API spend.

Future work:

1. Optional auto-cost summary table sourced from persisted token usage in SQLite.
2. Optional per-run cost field in report metadata.
