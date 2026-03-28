# Sample Results (Illustrative)

These are example outputs aligned with the current implementation.

## Run Metadata Example

| Field | Example Value |
| --- | --- |
| Run Label | first-real-run |
| Run Status | completed |
| Benchmark Version | 1.0.0 |
| Selected Dimensions | ["euphemism", "food_defaults", "framing_neutrality"] |
| Storage | SQLite (`speciesist_bias.db`) |
| HTML Report | `reports/first-real-run.html` |
| Latest Report Pointer | `reports/latest.html` |

## Example Leaderboard Shape

| Rank | Model | Euphemism | Food Defaults | Framing Neutrality | Composite |
| --- | --- | --- | --- | --- | --- |
| 1 | openai/gpt-4o | 8.1 | 6.9 | 8.4 | 7.8 |
| 2 | anthropic/claude-3-haiku | 7.4 | 6.1 | 7.2 | 6.9 |
| 3 | openai/gpt-4o-mini | 6.8 | 5.9 | 6.4 | 6.4 |

## Interpretation Notes

1. Higher normalized score means less speciesist signal for that dimension.
2. Composite is the arithmetic mean across available dimension scores.
3. Failures and refusals should be reviewed separately from score quality.

## Prompt-Level Row Shape

| Case ID | Dimension | Model | Status | Score | Latency (ms) |
| --- | --- | --- | --- | --- | --- |
| EUPH-001 | euphemism | openai/gpt-4o-mini | completed | 7.8 | 853.2 |
| FOOD-001 | food_defaults | openai/gpt-4o-mini | completed | 6.2 | 917.5 |
| FRAME-001 | framing_neutrality | openai/gpt-4o-mini | completed | 6.9 | 904.4 |

## Current vs Future

Current:

1. Report and dashboard consume persisted SQLite rows.
2. HTML export is standalone and suitable for sharing.

Future:

1. Optional run-to-run comparison summaries.
2. Optional richer trend tables over multiple runs.
