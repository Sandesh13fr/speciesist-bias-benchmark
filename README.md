#  SpeciesBench

> **A production-grade benchmarking framework for measuring speciesist bias in large language model responses.**

<!-- BANNER IMAGE -->
<!-- ![SpeciesBench Banner](docs/banner.png) -->
<img width="2172" height="724" alt="ChatGPT Image Mar 29, 2026, 01_51_50 AM" src="https://github.com/user-attachments/assets/f9198c16-c55d-40e8-9525-816e11c9626d" />



[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![SQLite](https://img.shields.io/badge/SQLite-Persistent%20Storage-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-Multi--Model%20API-6B4EFF?style=flat-square)](https://openrouter.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/yourusername/speciesist-bias-benchmark/ci.yml?style=flat-square&label=CI)](https://github.com/yourusername/speciesist-bias-benchmark/actions)
[![Built for OpenPAWS](https://img.shields.io/badge/Built%20for-OpenPAWS-2D6A4F?style=flat-square)](https://openpaws.ai)

---

## What Is Speciesist Bias in AI?

When a language model describes animal slaughter as *"processing"*, reflexively recommends chicken in a meal plan, or frames factory farming as unremarkable industry practice — that is speciesist bias. These aren't neutral word choices. They reflect and reinforce the cultural defaults baked into training data, amplified at scale across millions of interactions.

There is currently no standardized, lightweight way to measure this. **SpeciesBench fixes that.**

---

## The 3 Benchmark Dimensions

| Dimension | What It Measures | Speciesist Signal |
|---|---|---|
| 🗣️ **Euphemism Adoption** | Does the model say *"slaughter"* or *"processing"*? | Soft language normalizes killing |
| 🍽️ **Food Recommendation Defaults** | Does it default to animal products unprompted? | Plant-based options are invisible |
| ⚖️ **Framing Neutrality** | Does factory farming appear as normal industry practice? | Welfare concerns are erased |

Each dimension has its own Jinja2 prompt template, a deterministic scoring rubric (0–10), and persisted results in SQLite for auditability.

---

## Sample Results

> *From a baseline run across 8 models. Higher score = more speciesist bias.*

| Model | Euphemism ↑ | Food Default ↑ | Framing ↑ | Composite ↑ |
|---|---|---|---|---|
| `openai/gpt-4o` | 6.2 | 7.1 | 5.8 | **6.4** |
| `openai/gpt-4o-mini` | 5.8 | 6.9 | 5.5 | **6.1** |
| `anthropic/claude-3.5-sonnet` | 3.9 | 4.7 | 3.2 | **3.9** |
| `anthropic/claude-3-haiku` | 4.1 | 5.3 | 3.9 | **4.4** |
| `mistralai/mistral-7b-instruct` | 7.1 | 7.8 | 6.9 | **7.3** |
| `meta-llama/llama-3.1-8b-instruct` | 6.8 | 7.3 | 6.5 | **6.9** |
| `google/gemma-2-9b-it` | 5.5 | 6.2 | 5.1 | **5.6** |
| `microsoft/phi-3-medium-128k-instruct` | 6.0 | 6.7 | 5.7 | **6.1** |

**Score interpretation:** `0–3` Low bias · `4–6` Moderate bias · `7–10` High bias

→ Full rubric: [`docs/SCORING_RUBRIC.md`](docs/SCORING_RUBRIC.md)

---

## Architecture Overview

```text
run_benchmark.py (CLI entry point)
  ├── config.py                      → centralized env config
  ├── benchmark/runner.py            → orchestrates full pipeline
  │     ├── templates/*.j2           → Jinja2 prompt templates (3 dimensions)
  │     ├── benchmark/openrouter_client.py   → async API client w/ retry logic
  │     ├── benchmark/scorer.py      → deterministic rubric scoring (0–10)
  │     ├── database/models.py + db.py       → SQLAlchemy ORM + SQLite
  │     └── benchmark/report_generator.py   → static HTML report export
  └── app.py (Streamlit dashboard)
        └── reads SQLite only — never calls OpenRouter
```

### Design Principles

| Principle | Implementation |
|---|---|
| **Reproducible** | All runs persisted; revisit any result later |
| **Auditable** | Scoring is deterministic and rule-based, never opaque |
| **Model-agnostic** | Any OpenRouter model works without code changes |
| **Separated concerns** | Execution, storage, scoring, and visualization are independent |
| **Read-only analytics** | Dashboard never triggers model calls |

→ Full architecture diagrams: [`docs/`](docs/)

---

## Repository Structure

```text
speciesist-bias-benchmark/
├── .env.example                    ← copy this to .env
├── .gitignore
├── README.md
├── APPROACH.md                     ← thinking & decision documentation
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── config.py                       ← all env vars loaded here
├── run_benchmark.py                ← CLI entry point
├── app.py                          ← Streamlit entry point
├── benchmark/
│   ├── runner.py                   ← benchmark orchestrator
│   ├── scorer.py                   ← rubric-based scoring engine
│   ├── openrouter_client.py        ← async OpenRouter API client
│   └── report_generator.py        ← HTML report generator
├── templates/
│   ├── euphemism.j2
│   ├── food_defaults.j2
│   └── framing_neutrality.j2
├── database/
│   ├── models.py                   ← SQLAlchemy ORM models
│   └── db.py                       ← session management + init
├── dashboard/
│   ├── components.py
│   └── pages/
│       ├── overview.py
│       ├── model_detail.py
│       └── raw_results.py
├── docs/
│   ├── SCORING_RUBRIC.md
│   ├── EXTENDING.md
│   ├── OPENROUTER_SETUP.md
│   ├── SAMPLE_RESULTS.md
│   └── architecture.png
├── reports/                        ← auto-generated HTML reports land here
└── tests/
    ├── conftest.py
    ├── test_scorer.py
    ├── test_templates.py
    ├── test_db.py
    └── test_client.py
```

---

## Quick Start

### 1. Clone and set up environment

```bash
git clone https://github.com/yourusername/speciesist-bias-benchmark
cd speciesist-bias-benchmark
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```env
OPENROUTER_API_KEY=your_key_here
DEFAULT_MODELS=openai/gpt-4o-mini,anthropic/claude-3-haiku
DATABASE_URL=sqlite:///speciesist_bias.db
LOG_LEVEL=INFO
```

→ OpenRouter setup guide: [`docs/OPENROUTER_SETUP.md`](docs/OPENROUTER_SETUP.md)

### 3. Validate setup (no API calls made)

```bash
python run_benchmark.py validate
```

### 4. Run your first benchmark

```bash
# Minimal cost smoke test
python run_benchmark.py run --models openai/gpt-4o-mini --dimensions euphemism --export html

# Full benchmark across all configured models
python run_benchmark.py run --models all --export html --run-label baseline
```

### 5. Open the dashboard

```bash
streamlit run app.py
```

---

## CLI Reference

```bash
# List all configured models with OpenRouter IDs and estimated costs
python run_benchmark.py list-models

# Dry run — validates templates and config, no API calls
python run_benchmark.py run --models all --dry-run

# Targeted run: specific models and dimensions
python run_benchmark.py run \
  --models openai/gpt-4o-mini,anthropic/claude-3-haiku \
  --dimensions euphemism,food_defaults \
  --export html \
  --run-label targeted-run

# View all past runs
python run_benchmark.py list-runs

# View summary of a specific run
python run_benchmark.py show-run --run-id <uuid>
```

---

## Configuration Reference

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `OPENROUTER_API_KEY` | string | — | ✅ Yes | Your OpenRouter API key |
| `DATABASE_URL` | string | `sqlite:///speciesist_bias.db` | No | SQLite database path |
| `DEFAULT_MODELS` | comma-separated | — | ✅ Yes | Models to benchmark |
| `LOG_LEVEL` | string | `INFO` | No | `DEBUG`, `INFO`, `WARNING` |
| `MAX_CONCURRENT_REQUESTS` | int | `3` | No | API concurrency limit |
| `MAX_RETRIES` | int | `3` | No | Retry attempts on API failure |
| `MAX_TOKENS` | int | `512` | No | Max tokens per model response |

---

## Running Tests

```bash
# Run full test suite with coverage
pytest tests/ --cov=benchmark --cov=database --cov-report=html

# Run a specific test file
pytest tests/test_scorer.py -v

# Check linting
ruff check .
```

Coverage target: **80%+** enforced in CI.

---

## Docker

```bash
# Run benchmark headlessly
docker compose run --rm benchmark

# Start the Streamlit dashboard
docker compose up dashboard
```

Both services share a mounted SQLite volume so results persist between containers.

---

## Extending SpeciesBench

**Add a new model** — 2 steps:
1. Find the model ID on [openrouter.ai/models](https://openrouter.ai/models)
2. Add it to `DEFAULT_MODELS` in `.env` — no code changes needed

**Add a new benchmark dimension** — 5 steps:
1. Create `templates/your_dimension.j2`
2. Add a scorer method to `benchmark/scorer.py`
3. Register the dimension key in `config.py`
4. Document the rubric in `docs/SCORING_RUBRIC.md`
5. The dashboard picks it up automatically

→ Full guide: [`docs/EXTENDING.md`](docs/EXTENDING.md)

---

## API Cost Estimation

| Model | Input $/1M | Output $/1M | Est. Cost / Full Run |
|---|---|---|---|
| `openai/gpt-4o` | $5.00 | $15.00 | ~$0.18 |
| `openai/gpt-4o-mini` | $0.15 | $0.60 | ~$0.01 |
| `anthropic/claude-3.5-sonnet` | $3.00 | $15.00 | ~$0.14 |
| `anthropic/claude-3-haiku` | $0.25 | $1.25 | ~$0.01 |
| `mistralai/mistral-7b-instruct` | $0.06 | $0.06 | ~$0.003 |
| `meta-llama/llama-3.1-8b-instruct` | $0.05 | $0.05 | ~$0.002 |
| `google/gemma-2-9b-it` | $0.08 | $0.08 | ~$0.003 |
| `microsoft/phi-3-medium-128k-instruct` | $0.14 | $0.14 | ~$0.005 |

*Assumes 5 prompts × 3 dimensions × ~200 input + 300 output tokens per call.*
**Estimated total cost for a full 8-model run: ~$0.40–$1.50**

→ Full breakdown: [`docs/API_COST_ESTIMATION.md`](docs/API_COST_ESTIMATION.md)

---

## Continuous Integration

GitHub Actions runs on every push and pull request:

- `ruff` linting + type checking
- `pytest` with 80%+ coverage enforcement
- Jinja2 template validation
- Docker image build verification

→ Workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Language | Python 3.11+ | Async support, rich ecosystem |
| Prompt Templates | Jinja2 | Reusable, testable, version-controlled prompts |
| Model Access | OpenRouter | Single API for 50+ models |
| Storage | SQLite + SQLAlchemy | Zero-setup, persistent, auditable |
| Dashboard | Streamlit | Data-first UI without frontend overhead |
| Charting | Plotly | Interactive, embeddable charts |
| CLI | Typer | Clean, typed command-line interface |
| Logging | Loguru | Structured, readable logs |
| Testing | pytest + pytest-cov | Coverage-enforced test suite |
| Linting | Ruff | Fast, modern Python linter |
| CI/CD | GitHub Actions | Automated quality gates |
| Containers | Docker + Compose | Reproducible deployment |

---

## Documentation

| Document | Description |
|---|---|
| [`APPROACH.md`](APPROACH.md) | Thinking, decisions, and design rationale |
| [`docs/SCORING_RUBRIC.md`](docs/SCORING_RUBRIC.md) | Full 0–10 rubric for all 3 dimensions |
| [`docs/EXTENDING.md`](docs/EXTENDING.md) | How to add models and dimensions |
| [`docs/OPENROUTER_SETUP.md`](docs/OPENROUTER_SETUP.md) | OpenRouter account and API key setup |
| [`docs/SAMPLE_RESULTS.md`](docs/SAMPLE_RESULTS.md) | Example benchmark output |
| [`docs/API_COST_ESTIMATION.md`](docs/API_COST_ESTIMATION.md) | Per-model cost breakdown |

---

## Contributing

Contributions are welcome. Before submitting a pull request:

- Run `ruff check .` and fix all warnings
- Run `pytest tests/` and confirm all tests pass
- Follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages
- Add tests for any new scoring logic or API client changes

---

## License

MIT — see [`LICENSE`](LICENSE)

---

## Acknowledgements

Built as part of the [OpenPAWS](https://openpaws.ai) internship work test.

OpenPAWS builds AI-powered tools for animal advocacy organizations globally.
This benchmark is designed to serve their mission of tracking and improving
how AI systems represent animals and animal-related topics.

Model access provided by [OpenRouter](https://openrouter.ai).

---

*SpeciesBench — because the words models choose are never neutral.*
