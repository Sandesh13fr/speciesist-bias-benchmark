#  SpeciesBench

> **A production-grade benchmarking framework for measuring speciesist bias in large language model responses.**

<!-- BANNER IMAGE -->
<img width="2172" height="724" alt="ChatGPT Image Mar 29, 2026, 01_51_50 AM" src="https://github.com/user-attachments/assets/f9198c16-c55d-40e8-9525-816e11c9626d" />



[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![SQLite](https://img.shields.io/badge/SQLite-Persistent%20Storage-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-Multi--Model%20API-6B4EFF?style=flat-square)](https://openrouter.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/Sandesh13fr/speciesist-bias-benchmark/ci.yml?style=flat-square&label=CI)](https://github.com/Sandesh13fr/speciesist-bias-benchmark/actions)
[![Built for OpenPAWS](https://img.shields.io/badge/Built%20for-OpenPAWS-2D6A4F?style=flat-square)](https://openpaws.ai)

---

## What Is Speciesist Bias in AI?

When a language model describes animal slaughter as *"processing"*, reflexively recommends chicken in a meal plan, or frames factory farming as unremarkable industry practice — that is speciesist bias. These aren't neutral word choices. They reflect and reinforce the cultural defaults baked into training data, amplified at scale across millions of interactions.

There is currently no standardized, lightweight way to measure this. **SpeciesBench fixes that.**

---

## Scoring Convention

> **Higher score = more speciesist signal detected.**
> **Lower score = less speciesist bias in the model's response.**

This convention is consistent across all three benchmark dimensions, the scoring rubric ([`docs/SCORING_RUBRIC.md`](docs/SCORING_RUBRIC.md)), and all exported reports.

| Score Range | Interpretation |
|---|---|
| `0–3` | Low speciesist signal — model uses neutral or explicit language |
| `4–6` | Moderate signal — mixed or context-dependent framing |
| `7–10` | High speciesist signal — model normalizes harm or defaults to animal products |

---

## The 3 Benchmark Dimensions

| Dimension | What It Measures | Speciesist Signal |
|---|---|---|
| 🗣️ **Euphemism Adoption** | Does the model say *"slaughter"* or *"processing"*? | Soft language normalizes killing |
| 🍽️ **Food Recommendation Defaults** | Does it default to animal products unprompted? | Plant-based options are invisible |
| ⚖️ **Framing Neutrality** | Does factory farming appear as normal industry practice? | Welfare concerns are erased |

Each dimension has its own Jinja2 prompt template, a deterministic scoring rubric (0–10), and persisted results in SQLite for auditability.

---

## Baseline Results

> *Real benchmark run (`baseline-run`) executed against 5 OpenRouter models on 2026-03-28. Results are committed to [`docs/baseline_results.md`](docs/baseline_results.md) and the exported HTML report is available at [`reports/baseline-run.html`](reports/baseline-run.html).*
>
> **Lower composite score = less speciesist bias detected.**

| Model | Euphemism ↓ | Food Default ↓ | Framing ↓ | Composite ↓ |
|---|---|---|---|---|
| `anthropic/claude-3.5-sonnet` | 3.44 | 4.00 | 4.75 | **4.06** |
| `openai/gpt-4o` | 4.44 | 5.08 | 2.68 | **4.07** |
| `openai/gpt-4o-mini` | 3.77 | 6.25 | 2.37 | **4.13** |
| `deepseek/deepseek-chat` | 4.54 | 7.00 | 2.69 | **4.74** |
| `anthropic/claude-3-haiku` | 4.11 | 7.50 | 4.00 | **5.20** |

**Score interpretation:** `0–3` Low signal · `4–6` Moderate signal · `7–10` High speciesist signal

→ Full rubric: [`docs/SCORING_RUBRIC.md`](docs/SCORING_RUBRIC.md)
→ Versioned baseline evidence: [`docs/baseline_results.md`](docs/baseline_results.md)
→ Exported HTML report: [`reports/baseline-run.html`](reports/baseline-run.html)

---

## Architecture Overview

```text
run_benchmark.py (CLI entry point)
  ├── config.py                      → centralized env config
  ├── benchmark/runner.py            → orchestrates full pipeline
  │     ├── templates/*.j2           → Jinja2 prompt templates (3 dimensions)
  │     ├── benchmark/openrouter_client.py   → OpenRouter API client w/ retry + rate limiting
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
│   ├── openrouter_client.py        ← OpenRouter API client with retry/rate limiting
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
│   ├── SCORING_RUBRIC.md           ← canonical 0–10 rubric (higher = more biased)
│   ├── EXTENDING.md
│   ├── OPENROUTER_SETUP.md
│   ├── baseline_results.md         ← real committed baseline run results
│   └── API_COST_ESTIMATION.md
├── reports/
│   └── baseline-run.html           ← exported HTML report from baseline run
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
git clone https://github.com/Sandesh13fr/speciesist-bias-benchmark
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
python run_benchmark.py --dry-run --models all
```

### 4. Run your first benchmark

```bash
# Minimal cost smoke test
python run_benchmark.py --models openai/gpt-4o-mini --dimensions euphemism --export html --run-label smoke-run

# Full benchmark across all configured models
python run_benchmark.py --models all --export html --run-label baseline-run
```

### 5. Open the dashboard

```bash
streamlit run app.py
```

---

## CLI Reference

```bash
# List all configured models with OpenRouter IDs and estimated costs
python run_benchmark.py --list-models

# Dry run — validates templates and config, no API calls
python run_benchmark.py --models all --dry-run

# Targeted run: specific models and dimensions
python run_benchmark.py \
  --models openai/gpt-4o-mini,anthropic/claude-3-haiku \
  --dimensions euphemism,food_defaults \
  --export html \
  --run-label targeted-run
```

---

## Configuration Reference

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `OPENROUTER_API_KEY` | string | — | ✅ Yes | Your OpenRouter API key |
| `DATABASE_URL` | string | `sqlite:///speciesist_bias.db` | No | SQLite database path |
| `DEFAULT_MODELS` | comma-separated | — | ✅ Yes | Models to benchmark |
| `LOG_LEVEL` | string | `INFO` | No | `DEBUG`, `INFO`, `WARNING` |
| `REQUEST_TIMEOUT_SECONDS` | int | `60` | No | HTTP timeout per API call |
| `MAX_RETRIES` | int | `5` | No | Retry attempts on API failure |
| `DEFAULT_MAX_TOKENS` | int | `350` | No | Max tokens per model response |
| `RATE_LIMIT_RPM` | int | `30` | No | Client-side API request cap per minute |

---

## Running Tests

```bash
# Run full test suite with coverage output (optional local quality signal)
pytest tests/ --cov=benchmark --cov=database --cov-report=html

# Run a specific test file
pytest tests/test_scorer.py -v

# Check linting
ruff check .
```

Note: CI currently validates linting, tests, and template rendering. Coverage is available locally via `pytest-cov`.

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
4. Document the rubric in `docs/SCORING_RUBRIC.md` — remember: **higher score = more speciesist signal**
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

- `ruff` linting
- `pytest` execution
- Jinja2 template validation
- read-only dashboard note (no live API calls)

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
| CLI | argparse | Explicit, lightweight command-line interface |
| Logging | Python logging | Structured, configurable runtime logs |
| Testing | pytest + pytest-cov | Test suite with optional local coverage reports |
| Linting | Ruff | Fast, modern Python linter |
| CI/CD | GitHub Actions | Automated quality gates |
| Containers | Docker + Compose | Reproducible deployment |

---

## Documentation

| Document | Description |
|---|---|
| [`APPROACH.md`](APPROACH.md) | Thinking, decisions, and design rationale |
| [`docs/SCORING_RUBRIC.md`](docs/SCORING_RUBRIC.md) | Full 0–10 rubric — **higher score = more speciesist signal** |
| [`docs/EXTENDING.md`](docs/EXTENDING.md) | How to add models and dimensions |
| [`docs/OPENROUTER_SETUP.md`](docs/OPENROUTER_SETUP.md) | OpenRouter account and API key setup |
| [`docs/baseline_results.md`](docs/baseline_results.md) | Real committed 5-model baseline run with evidence |
| [`docs/API_COST_ESTIMATION.md`](docs/API_COST_ESTIMATION.md) | Per-model cost breakdown |
| [`reports/baseline-run.html`](reports/baseline-run.html) | Exported HTML report from the baseline run |

---

## Contributing

Contributions are welcome. Before submitting a pull request:

- Run `ruff check .` and fix all warnings
- Run `pytest tests/` and confirm all tests pass
- Follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages
- Add tests for any new scoring logic or API client changes
- Ensure any new rubric documentation uses the canonical convention: **higher score = more speciesist signal detected**

---

## License

MIT — see [`LICENSE`](LICENSE)

---

## Acknowledgements

Built as part of the [OpenPAWS](https://openpaws.ai) internship work test.

OpenPAWS builds AI-powered tools for animal advocacy organizations globally.
This benchmark is designed to serve their mission of tracking and improving
how AI systems represent animals and animal-related topics.

---

*SpeciesBench — because the words models choose are never neutral.*