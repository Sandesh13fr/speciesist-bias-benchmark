"""Application configuration for the speciesist bias benchmark."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables.

    Attributes:
        openrouter_api_key: API key for OpenRouter requests.
        openrouter_base_url: Base URL for OpenRouter API.
        openrouter_app_name: Optional app name header for attribution.
        openrouter_site_url: Optional site URL header for attribution.
        default_models: Comma-separated default model IDs.
        default_temperature: Sampling temperature for generation.
        default_max_tokens: Max tokens per completion request.
        request_timeout_seconds: HTTP request timeout in seconds.
        max_retries: Retry attempts for transient failures.
        rate_limit_rpm: Client-side request rate limit per minute.
        database_url: SQLAlchemy SQLite URL.
        reports_dir: Path where generated reports are written.
        templates_dir: Root path for all Jinja2 templates.
        log_level: Python logging level.
    """

    openrouter_api_key: str
    openrouter_base_url: str
    openrouter_app_name: str
    openrouter_site_url: str
    default_models: str
    default_temperature: float
    default_max_tokens: int
    request_timeout_seconds: int
    max_retries: int
    rate_limit_rpm: int
    database_url: str
    reports_dir: Path
    templates_dir: Path
    log_level: str


ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)


def _get_required_env(name: str) -> str:
    """Return a required environment variable.

    Args:
        name: Environment variable name.

    Returns:
        Environment variable value.

    Raises:
        ValueError: If the variable is not set.
    """
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def load_settings(require_api_key: bool = True) -> Settings:
    """Load application settings from environment variables.

    Args:
        require_api_key: Whether OPENROUTER_API_KEY must be present.

    Returns:
        Settings object with parsed values.
    """
    project_root = Path(__file__).resolve().parent

    return Settings(
        openrouter_api_key=(
            _get_required_env("OPENROUTER_API_KEY")
            if require_api_key
            else os.getenv("OPENROUTER_API_KEY", "").strip()
        ),
        openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip(),
        openrouter_app_name=os.getenv("OPENROUTER_APP_NAME", "Speciesist Bias Benchmark").strip(),
        openrouter_site_url=os.getenv("OPENROUTER_SITE_URL", "").strip(),
        default_models=os.getenv("DEFAULT_MODELS", "").strip(),
        default_temperature=float(os.getenv("DEFAULT_TEMPERATURE", "0.2")),
        default_max_tokens=int(os.getenv("DEFAULT_MAX_TOKENS", "350")),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "60")),
        max_retries=int(os.getenv("MAX_RETRIES", "5")),
        rate_limit_rpm=int(os.getenv("RATE_LIMIT_RPM", "30")),
        database_url=os.getenv("DATABASE_URL", "sqlite:///speciesist_bias.db").strip(),
        reports_dir=project_root / os.getenv("REPORTS_DIR", "reports"),
        templates_dir=project_root / os.getenv("TEMPLATES_DIR", "templates"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
