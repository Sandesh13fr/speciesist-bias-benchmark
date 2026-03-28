## Repository Structure
```text
SpeciesBench/
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
|   `-- SCORING_RUBRIC.md
|-- tests/
|   |-- test_scorer.py
|   |-- test_templates.py
|   |-- test_db.py
|   `-- test_client.py
`-- reports/ (generated)
```
