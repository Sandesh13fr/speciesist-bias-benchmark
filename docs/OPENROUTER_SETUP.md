# OpenRouter Setup

This guide reflects the current runnable root project.

## 1. Configure Environment Variables

Create `.env` from `.env.example` and set:

```env
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_MODELS=openai/gpt-4o-mini,openai/gpt-4o,anthropic/claude-3-haiku
DATABASE_URL=sqlite:///speciesist_bias.db
LOG_LEVEL=INFO
```

Rules:

1. Never hardcode API keys in source code.
2. Never commit `.env`.
3. Commit `.env.example` only.

## 2. Verify Setup

```powershell
python run_benchmark.py --help
python run_benchmark.py --list-models
```

## 3. Run a Dry Run (No API Calls)

```powershell
python run_benchmark.py --models all --dry-run --max-prompts-per-dimension 1
```

## 4. Run a Real Benchmark

```powershell
python run_benchmark.py --models all --export html --run-label first-real-run
```

This command requires a valid `OPENROUTER_API_KEY`.

## 5. View Results

Dashboard (read-only):

```powershell
streamlit run app.py
```

Reports:

1. Generated HTML reports are saved in `reports/`.
2. `reports/latest.html` points to the newest exported report.

## 6. Docker Option

```powershell
docker compose run --rm benchmark
docker compose up dashboard
```

Compose services share SQLite persistence through a mounted data volume.

## Current vs Future

Current:

1. OpenRouter is used only by benchmark execution paths.
2. Streamlit dashboard never calls OpenRouter.

Future:

1. Optional richer setup diagnostics and key validation commands in CLI.
