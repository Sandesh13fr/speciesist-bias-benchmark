# Baseline Benchmark Evidence

This document is a repository-tracked summary of the baseline benchmark run.

## Baseline Run Details

- Run ID: 2
- Run Label: baseline-run
- Status: completed
- Prompt dimensions: euphemism, food_defaults, framing_neutrality
- Distinct OpenRouter models benchmarked: 5
- Total responses stored: 30
- SQLite source: speciesist_bias.db
- Generated report artifact (SQLite-native): reports/run_2_baseline-run.html
- Machine-readable snapshot: docs/baseline_run_2.json

## Model Comparison (Run ID 2)

| Rank | Model | Euphemism | Food Defaults | Framing Neutrality | Composite |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | anthropic/claude-3.5-sonnet | 6.56 | 6.00 | 5.25 | 5.94 |
| 2 | openai/gpt-4o | 5.56 | 4.92 | 7.32 | 5.93 |
| 3 | openai/gpt-4o-mini | 6.23 | 3.75 | 7.63 | 5.87 |
| 4 | deepseek/deepseek-chat | 5.46 | 3.00 | 7.31 | 5.26 |
| 5 | anthropic/claude-3-haiku | 5.89 | 2.50 | 6.00 | 4.80 |

## Interpretation

- Higher scores indicate lower speciesist signal under the current deterministic rubric.
- Composite score is the arithmetic mean of available dimension scores.
- Results are reproducible from persisted rows in SQLite and can be re-rendered via HTML reporting.
