"""CLI entrypoint for running the benchmark headlessly."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from benchmark.runner import (
    BenchmarkRunner,
    default_prompt_cases,
    render_prompt_template,
)
from config import load_settings
from database.db import init_db
from logging_config import configure_logging

logger = logging.getLogger(__name__)

ALLOWED_DIMENSIONS = ["euphemism", "food_defaults", "framing_neutrality"]


def parse_models_arg(raw: str, default_models: list[str]) -> list[str]:
    """Parse the ``--models`` argument.

    Args:
        raw: Raw models argument value.
        default_models: Default model IDs from settings.

    Returns:
        Resolved list of model IDs.

    Raises:
        ValueError: If no model IDs can be resolved.
    """
    value = raw.strip()
    if value.lower() == "all":
        models = [item.strip() for item in default_models if item.strip()]
    else:
        models = [item.strip() for item in value.split(",") if item.strip()]

    if not models:
        raise ValueError(
            "No models resolved. Provide --models model_a,model_b or set DEFAULT_MODELS for --models all."
        )
    return models


def parse_dimensions_arg(raw: str | None) -> list[str] | None:
    """Parse and validate ``--dimensions``.

    Args:
        raw: Optional comma-separated dimensions.

    Returns:
        None when omitted, otherwise a validated list of dimensions.

    Raises:
        ValueError: If no valid dimensions are provided.
    """
    if raw is None:
        return None

    dimensions = [item.strip() for item in raw.split(",") if item.strip()]
    if not dimensions:
        raise ValueError("No dimensions provided.")

    unknown = [item for item in dimensions if item not in ALLOWED_DIMENSIONS]
    if unknown:
        raise ValueError(
            f"Unknown dimensions: {', '.join(unknown)}. Allowed: {', '.join(ALLOWED_DIMENSIONS)}"
        )
    return dimensions


def build_parser() -> argparse.ArgumentParser:
    """Build the benchmark CLI argument parser.

    Returns:
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Run speciesist bias benchmark in headless mode.",
    )
    parser.add_argument(
        "--models",
        default="all",
        help="Use 'all' or a comma-separated list of model IDs.",
    )
    parser.add_argument(
        "--dimensions",
        default=None,
        help="Optional comma-separated dimensions (euphemism,food_defaults,framing_neutrality).",
    )
    parser.add_argument(
        "--max-prompts-per-dimension",
        type=int,
        default=2,
        help="Maximum prompt cases to run per selected dimension.",
    )
    parser.add_argument(
        "--export",
        choices=["none", "html"],
        default="none",
        help="Optional report export format.",
    )
    parser.add_argument(
        "--run-label",
        default=None,
        help="Optional run label used for persistence/reporting.",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Print configured default models and exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render prompts and log the planned execution without API calls.",
    )
    return parser


def _parse_default_models(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _run_dry_run(
    *,
    templates_dir: Path,
    models: list[str],
    dimensions: list[str] | None,
    max_prompts_per_dimension: int,
    run_label: str | None,
) -> int:
    """Render selected prompts and log what an execution would perform."""
    selected_dimensions = dimensions or ALLOWED_DIMENSIONS
    prompt_limit = max(1, max_prompts_per_dimension)
    inventory = default_prompt_cases()

    total_prompts = 0
    logger.info("Dry run mode enabled. No OpenRouter requests will be sent.")
    logger.info("Run label: %s", run_label or "(auto-generated)")
    logger.info("Models (%d): %s", len(models), ", ".join(models))
    logger.info("Dimensions (%d): %s", len(selected_dimensions), ", ".join(selected_dimensions))
    logger.info("Max prompts per dimension: %d", prompt_limit)

    for dimension in selected_dimensions:
        cases = inventory.get(dimension, [])[:prompt_limit]
        logger.info("Dimension '%s': %d prompt(s)", dimension, len(cases))
        for case in cases:
            template_path = templates_dir / case.template_name
            rendered = render_prompt_template(template_path=template_path, context=case.variables)
            snippet = rendered.replace("\n", " ").strip()
            if len(snippet) > 140:
                snippet = f"{snippet[:140]}..."
            logger.info(
                "Would execute case=%s model_count=%d template=%s prompt_preview=%s",
                case.case_id,
                len(models),
                case.template_name,
                snippet,
            )
            total_prompts += 1

    logger.info(
        "Dry run summary: rendered_prompts=%d planned_calls=%d",
        total_prompts,
        total_prompts * len(models),
    )
    return 0


def main() -> int:
    """Run benchmark execution from CLI.

    Returns:
        Process exit code (0 on success, non-zero on failure).
    """
    parser = build_parser()
    args = parser.parse_args()

    try:
        settings = load_settings(require_api_key=not (args.list_models or args.dry_run))
        configure_logging(settings.log_level)

        default_models = _parse_default_models(settings.default_models)
        models = parse_models_arg(args.models, default_models)
        dimensions = parse_dimensions_arg(args.dimensions)

        if args.max_prompts_per_dimension < 1:
            raise ValueError("--max-prompts-per-dimension must be >= 1")

        if args.list_models:
            print("Configured/default models:")
            for model in default_models:
                print(model)
            if not default_models:
                print("(none configured)")
            return 0

        init_db(settings.database_url)

        if args.dry_run:
            return _run_dry_run(
                templates_dir=Path(settings.templates_dir),
                models=models,
                dimensions=dimensions,
                max_prompts_per_dimension=args.max_prompts_per_dimension,
                run_label=args.run_label,
            )

        runner = BenchmarkRunner(settings=settings)
        summary = runner.execute(
            models=models,
            dimensions=dimensions,
            max_prompts_per_dimension=args.max_prompts_per_dimension,
            export_html=args.export == "html",
            run_label=args.run_label,
        )

        logger.info("Run completed")
        logger.info("- Run ID: %s", summary.run_id)
        logger.info("- Run Label: %s", summary.run_label)
        logger.info("- Status: %s", summary.status)
        logger.info("- Attempted Calls: %d", summary.attempted_calls)
        logger.info("- Successful Calls: %d", summary.successful_calls)
        logger.info("- Failed Calls: %d", summary.failed_calls)
        logger.info("- Refusals: %d", summary.refusal_count)
        logger.info("- Scored: %d", summary.scored_count)
        logger.info("- Duration (s): %.3f", summary.duration_seconds)
        if summary.report_path:
            logger.info("- HTML Report: %s", summary.report_path)

        return 0
    except ValueError as exc:
        logging.getLogger(__name__).error("Invalid CLI/config input: %s", exc)
        return 2
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        logging.getLogger(__name__).exception("Unrecoverable benchmark setup/runtime failure: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
