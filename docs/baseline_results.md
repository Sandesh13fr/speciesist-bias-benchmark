# Baseline Benchmark Evidence

This document records the repository-tracked baseline run.

## Run Metadata

| Field | Value |
| --- | --- |
| Run ID | 2 |
| Run Label | baseline-run |
| Status | completed |
| Dimensions | euphemism, food_defaults, framing_neutrality |
| Distinct OpenRouter models | 5 |
| Total responses | 30 |
| SQLite source | speciesist_bias.db |
| Baseline report | reports/baseline-run.html |
| Machine-readable snapshot | docs/baseline_run_2.json |

## Model Comparison (Run 2)

| Rank | Model | Euphemism | Food Defaults | Framing Neutrality | Composite |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | anthropic/claude-3.5-sonnet | 3.44 | 4.00 | 4.75 | 4.06 |
| 2 | openai/gpt-4o | 4.44 | 5.08 | 2.68 | 4.07 |
| 3 | openai/gpt-4o-mini | 3.77 | 6.25 | 2.37 | 4.13 |
| 4 | deepseek/deepseek-chat | 4.54 | 7.00 | 2.68 | 4.74 |
| 5 | anthropic/claude-3-haiku | 4.11 | 7.50 | 4.00 | 5.20 |

## Interpretation

- Higher scores indicate stronger detected speciesist signal under the deterministic rubric.
- Lower composite score indicates less speciesist bias for this run.
- Results are reproducible from persisted SQLite rows and can be re-rendered as HTML.
