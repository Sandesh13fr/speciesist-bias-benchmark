# Research Notes

## Objective

The benchmark measures speciesist bias in model outputs using deterministic scoring across three dimensions:

1. euphemism adoption
2. default food recommendations
3. framing neutrality

## Why This Matters

Speciesist bias often appears as subtle normalization rather than explicit hostility. Reliable measurement supports practical iteration for advocacy-aligned AI workflows.

## Current Technical Implementation

1. Prompt templates: Jinja2 files under `templates/`.
2. Execution: headless CLI in `run_benchmark.py` and orchestration in `benchmark/runner.py`.
3. API layer: OpenRouter client in `benchmark/openrouter_client.py`.
4. Scoring: deterministic rubric in `benchmark/scorer.py`.
5. Persistence: SQLite + SQLAlchemy in `database/`.
6. Reporting: static HTML generation in `benchmark/report_generator.py`.
7. Visualization: read-only Streamlit dashboard in `app.py` + `dashboard/`.

## Current Evaluation Principles

1. Keep scoring explainable and auditable.
2. Persist raw outputs and score breakdown metadata.
3. Separate execution from analytics presentation.
4. Avoid hidden online dependencies in dashboard/report viewing.

## Risks and Limitations (Current)

1. Rule-based scoring can miss nuanced phrasing.
2. Prompt inventory quality strongly affects outcomes.
3. Current benchmark is English-first.

## Future Work (Not Yet Implemented)

1. Additional dimensions and multilingual coverage.
2. Human review loops for contested outputs.
3. Run-to-run drift analytics and calibration workflows.

## References

1. OpenRouter documentation: https://openrouter.ai/docs
2. SQLAlchemy documentation: https://docs.sqlalchemy.org
3. Streamlit documentation: https://docs.streamlit.io
4. Jinja documentation: https://jinja.palletsprojects.com
5. pytest documentation: https://docs.pytest.org
41. OpenRouter Gemma 2 9B IT model page — https://openrouter.ai/google/gemma-2-9b-it
42. OpenRouter Phi-3 Medium 128k Instruct model page — https://openrouter.ai/microsoft/phi-3-medium-128k-instruct
43. OpenRouter DeepSeek Chat model page — https://openrouter.ai/deepseek/deepseek-chat
44. OpenRouter Qwen 2.5 7B Instruct model page — https://openrouter.ai/qwen/qwen-2.5-7b-instruct
