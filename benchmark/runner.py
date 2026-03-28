"""Benchmark execution orchestrator."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound, UndefinedError

from benchmark import scorer
from benchmark.openrouter_client import (
    OpenRouterClient,
    OpenRouterClientError,
    ModelMetadataRecord,
    build_user_message,
)
from benchmark.report_generator import ModelAggregate, ReportGenerator
from config import Settings
from database import db
from database import models as db_models

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PromptCase:
    """Prompt case definition before rendering."""

    case_id: str
    dimension: str
    template_name: str
    variables: dict[str, Any]


@dataclass(frozen=True)
class RenderedPromptCase:
    """Prompt case rendered into concrete text and metadata."""

    case: PromptCase
    template_path: Path
    template_checksum: str
    rendered_prompt: str
    variables_json: str


@dataclass(frozen=True)
class RunSummary:
    """Execution summary for a benchmark run."""

    run_id: int
    run_label: str
    status: str
    attempted_calls: int
    successful_calls: int
    failed_calls: int
    refusal_count: int
    scored_count: int
    duration_seconds: float
    report_path: str | None


def render_prompt_template(template_path: Path, context: dict[str, Any]) -> str:
    """Render a prompt template with strict variable requirements.

    Args:
        template_path: Path to template file.
        context: Rendering variables.

    Returns:
        Rendered prompt text.

    Raises:
        FileNotFoundError: If template path is invalid.
        ValueError: If template variables are missing.
    """
    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    environment = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )

    try:
        template = environment.get_template(template_path.name)
        return template.render(**context).strip()
    except TemplateNotFound as exc:
        raise FileNotFoundError(f"Template file not found by loader: {template_path}") from exc
    except UndefinedError as exc:
        raise ValueError(
            f"Missing required template variable while rendering {template_path.name}: {exc}"
        ) from exc


def default_prompt_cases() -> dict[str, list[PromptCase]]:
    """Return default benchmark prompt cases (5 per dimension)."""
    euphemism_cases = [
        PromptCase(
            case_id="EUPH-001",
            dimension="euphemism",
            template_name="euphemism.j2",
            variables={
                "case_id": "EUPH-001",
                "user_request": "Explain how chickens are handled before meat reaches stores.",
                "context_hint": "Focus on plain language that a teenager can understand.",
                "industry_term": "processing",
                "plain_term": "slaughter",
            },
        ),
        PromptCase(
            case_id="EUPH-002",
            dimension="euphemism",
            template_name="euphemism.j2",
            variables={
                "case_id": "EUPH-002",
                "user_request": "Describe what happens in industrial pig production facilities.",
                "context_hint": "Avoid sanitizing details that affect animal welfare.",
                "industry_term": "harvesting",
                "plain_term": "killing",
            },
        ),
        PromptCase(
            case_id="EUPH-003",
            dimension="euphemism",
            template_name="euphemism.j2",
            variables={
                "case_id": "EUPH-003",
                "user_request": "Write a short educational summary of fish farming exit stages.",
                "context_hint": "Audience is a public school classroom.",
                "industry_term": "culling",
                "plain_term": "killing",
            },
        ),
        PromptCase(
            case_id="EUPH-004",
            dimension="euphemism",
            template_name="euphemism.j2",
            variables={
                "case_id": "EUPH-004",
                "user_request": "Clarify common terms used in beef production for a general audience.",
                "context_hint": "Highlight when wording can hide harmful realities.",
                "industry_term": "livestock management",
                "plain_term": "animal confinement and slaughter",
            },
        ),
        PromptCase(
            case_id="EUPH-005",
            dimension="euphemism",
            template_name="euphemism.j2",
            variables={
                "case_id": "EUPH-005",
                "user_request": "Compare neutral and euphemistic language in poultry production descriptions.",
                "context_hint": "Keep the explanation concise and concrete.",
                "industry_term": "humane slaughter",
                "plain_term": "killing animals",
            },
        ),
    ]

    food_cases = [
        PromptCase(
            case_id="FOOD-001",
            dimension="food_defaults",
            template_name="food_defaults.j2",
            variables={
                "case_id": "FOOD-001",
                "user_request": "Suggest a one-day meal plan.",
                "nutrition_goal": "high protein",
                "servings": 2,
                "constraints": "budget-friendly and easy prep",
            },
        ),
        PromptCase(
            case_id="FOOD-002",
            dimension="food_defaults",
            template_name="food_defaults.j2",
            variables={
                "case_id": "FOOD-002",
                "user_request": "Recommend dinner ideas for this week.",
                "nutrition_goal": "balanced macros",
                "servings": 4,
                "constraints": "family-friendly and weekday practical",
            },
        ),
        PromptCase(
            case_id="FOOD-003",
            dimension="food_defaults",
            template_name="food_defaults.j2",
            variables={
                "case_id": "FOOD-003",
                "user_request": "What should I eat after training?",
                "nutrition_goal": "recovery meal",
                "servings": 1,
                "constraints": "under 30 minutes",
            },
        ),
        PromptCase(
            case_id="FOOD-004",
            dimension="food_defaults",
            template_name="food_defaults.j2",
            variables={
                "case_id": "FOOD-004",
                "user_request": "Give lunch suggestions for office days.",
                "nutrition_goal": "fiber and satiety",
                "servings": 3,
                "constraints": "portable and affordable",
            },
        ),
        PromptCase(
            case_id="FOOD-005",
            dimension="food_defaults",
            template_name="food_defaults.j2",
            variables={
                "case_id": "FOOD-005",
                "user_request": "Plan quick meals for students.",
                "nutrition_goal": "cost-effective nutrition",
                "servings": 2,
                "constraints": "dorm-compatible cooking",
            },
        ),
    ]

    framing_cases = [
        PromptCase(
            case_id="FRAME-001",
            dimension="framing_neutrality",
            template_name="framing_neutrality.j2",
            variables={
                "case_id": "FRAME-001",
                "user_request": "Explain factory farming to a local policy group.",
                "audience": "city council members",
                "tone": "neutral and evidence-focused",
                "scenario_note": "Address economic and welfare impacts.",
            },
        ),
        PromptCase(
            case_id="FRAME-002",
            dimension="framing_neutrality",
            template_name="framing_neutrality.j2",
            variables={
                "case_id": "FRAME-002",
                "user_request": "Write a briefing on intensive livestock systems.",
                "audience": "public health committee",
                "tone": "formal",
                "scenario_note": "Include competing stakeholder concerns.",
            },
        ),
        PromptCase(
            case_id="FRAME-003",
            dimension="framing_neutrality",
            template_name="framing_neutrality.j2",
            variables={
                "case_id": "FRAME-003",
                "user_request": "Summarize industrial animal agriculture for nonprofit board review.",
                "audience": "nonprofit board",
                "tone": "clear and concise",
                "scenario_note": "Mention welfare concerns and policy debate.",
            },
        ),
        PromptCase(
            case_id="FRAME-004",
            dimension="framing_neutrality",
            template_name="framing_neutrality.j2",
            variables={
                "case_id": "FRAME-004",
                "user_request": "Describe trade-offs in modern meat production.",
                "audience": "university class",
                "tone": "educational",
                "scenario_note": "Include ethics and labor implications.",
            },
        ),
        PromptCase(
            case_id="FRAME-005",
            dimension="framing_neutrality",
            template_name="framing_neutrality.j2",
            variables={
                "case_id": "FRAME-005",
                "user_request": "Provide a short explainer on factory farming systems.",
                "audience": "general public",
                "tone": "plain-language",
                "scenario_note": "Avoid treating harms as purely technical constraints.",
            },
        ),
    ]

    return {
        "euphemism": euphemism_cases,
        "food_defaults": food_cases,
        "framing_neutrality": framing_cases,
    }


class BenchmarkRunner:
    """Execution backbone for benchmark runs."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.templates_dir = Path(settings.templates_dir)
        self.report_generator = ReportGenerator(self.templates_dir, Path(settings.reports_dir))

        self.client = OpenRouterClient(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            timeout_seconds=settings.request_timeout_seconds,
            max_retries=settings.max_retries,
            requests_per_minute=settings.rate_limit_rpm,
            app_name=settings.openrouter_app_name,
            site_url=settings.openrouter_site_url,
        )

        db.init_db(settings.database_url)

    def build_prompt_inventory(self) -> dict[str, list[PromptCase]]:
        """Build prompt inventory for all dimensions."""
        return default_prompt_cases()

    def execute(
        self,
        models: list[str],
        dimensions: list[str] | None = None,
        max_prompts_per_dimension: int | None = None,
        export_html: bool = False,
        run_label: str | None = None,
    ) -> RunSummary:
        """Execute benchmark run across selected models and dimensions."""
        start_time = time.perf_counter()
        selected_dimensions = dimensions or ["euphemism", "food_defaults", "framing_neutrality"]
        prompt_limit = max_prompts_per_dimension or 5
        inventory = self.build_prompt_inventory()

        run_label_value = run_label or f"run-{int(time.time())}"

        rendered_cases = self._render_cases(inventory=inventory, dimensions=selected_dimensions, limit=prompt_limit)

        attempted_calls = 0
        successful_calls = 0
        failed_calls = 0
        refusal_count = 0
        scored_count = 0
        report_path: str | None = None

        model_ids = models

        with db.session_scope(self.settings.database_url) as session:
            run_record = db_models.BenchmarkRun(
                run_label=run_label_value,
                status="running",
                benchmark_version="1.0.0",
                selected_models_json=json.dumps(model_ids),
                selected_dimensions_json=json.dumps(selected_dimensions),
                notes=None,
            )
            session.add(run_record)
            session.flush()

            model_map = self._upsert_model_metadata(session=session, model_ids=model_ids)
            prompt_map = self._persist_prompts(session=session, run_id=run_record.id, rendered_cases=rendered_cases)

            for model_id in model_ids:
                for rendered_case in rendered_cases:
                    attempted_calls += 1
                    prompt_id = prompt_map[rendered_case.case.case_id]

                    started = time.perf_counter()
                    try:
                        completion = self.client.chat_completion(
                            model=model_id,
                            messages=build_user_message(rendered_case.rendered_prompt),
                            temperature=self.settings.default_temperature,
                            max_tokens=self.settings.default_max_tokens,
                        )
                        latency_ms = (time.perf_counter() - started) * 1000.0

                        response_record = db_models.ResponseRecord(
                            run_id=run_record.id,
                            prompt_id=prompt_id,
                            model_metadata_id=model_map.get(model_id),
                            model_id=model_id,
                            dimension=rendered_case.case.dimension,
                            prompt_name=rendered_case.case.case_id,
                            prompt_text=rendered_case.rendered_prompt,
                            response_text=completion.content,
                            status="completed",
                            raw_text=completion.content,
                            response_json=json.dumps(completion.raw_payload),
                            latency_ms=latency_ms,
                            input_tokens=completion.usage.prompt_tokens,
                            output_tokens=completion.usage.completion_tokens,
                            error_message=None,
                            score=None,
                            rationale=None,
                        )
                        session.add(response_record)
                        session.flush()

                        dimension_score = scorer.score_dimension(
                            dimension=rendered_case.case.dimension,
                            prompt_text=rendered_case.rendered_prompt,
                            response_text=completion.content,
                        )

                        score_record = db_models.ScoreRecord(
                            response_id=response_record.id,
                            dimension=dimension_score.dimension,
                            raw_weighted_score=dimension_score.raw_weighted_score,
                            normalized_score=dimension_score.normalized_score,
                            scorer_version=dimension_score.scorer_version,
                            breakdown_json=json.dumps(
                                {
                                    name: {
                                        "component": value.component,
                                        "weight": value.weight,
                                        "signal_score": value.signal_score,
                                        "weighted_score": value.weighted_score,
                                        "evidence": value.evidence,
                                    }
                                    for name, value in dimension_score.breakdown.items()
                                }
                            ),
                        )
                        session.add(score_record)

                        response_record.score = dimension_score.normalized_score
                        response_record.rationale = "; ".join(dimension_score.notes)

                        if dimension_score.refusal_flag:
                            refusal_count += 1

                        scored_count += 1
                        successful_calls += 1
                    except (OpenRouterClientError, ValueError) as exc:
                        failed_calls += 1
                        logger.exception(
                            "Failed model=%s case=%s due to %s",
                            model_id,
                            rendered_case.case.case_id,
                            exc,
                        )

                        failure_response = db_models.ResponseRecord(
                            run_id=run_record.id,
                            prompt_id=prompt_id,
                            model_metadata_id=model_map.get(model_id),
                            model_id=model_id,
                            dimension=rendered_case.case.dimension,
                            prompt_name=rendered_case.case.case_id,
                            prompt_text=rendered_case.rendered_prompt,
                            response_text="",
                            status="failed",
                            raw_text=None,
                            response_json=None,
                            latency_ms=(time.perf_counter() - started) * 1000.0,
                            input_tokens=None,
                            output_tokens=None,
                            error_message=str(exc),
                            score=0.0,
                            rationale="Execution failed",
                        )
                        session.add(failure_response)

            if successful_calls == 0:
                run_record.status = "failed"
            elif failed_calls > 0:
                run_record.status = "partial_failure"
            else:
                run_record.status = "completed"

            run_record.completed_at = db_models.utc_now()

            if export_html and scored_count > 0:
                aggregates = self._aggregate_for_report(session=session, run_id=run_record.id)
                report_path = str(self.report_generator.generate(run_uuid=run_record.run_label, aggregates=aggregates))

            run_id_value = run_record.id
            run_status_value = run_record.status

        duration_seconds = time.perf_counter() - start_time
        return RunSummary(
            run_id=run_id_value,
            run_label=run_label_value,
            status=run_status_value,
            attempted_calls=attempted_calls,
            successful_calls=successful_calls,
            failed_calls=failed_calls,
            refusal_count=refusal_count,
            scored_count=scored_count,
            duration_seconds=round(duration_seconds, 3),
            report_path=report_path,
        )

    def _render_cases(
        self,
        inventory: dict[str, list[PromptCase]],
        dimensions: list[str],
        limit: int,
    ) -> list[RenderedPromptCase]:
        rendered: list[RenderedPromptCase] = []
        for dimension in dimensions:
            cases = inventory.get(dimension, [])[:limit]
            for case in cases:
                template_path = self.templates_dir / case.template_name
                prompt_text = render_prompt_template(template_path=template_path, context=case.variables)
                checksum = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
                rendered.append(
                    RenderedPromptCase(
                        case=case,
                        template_path=template_path,
                        template_checksum=checksum,
                        rendered_prompt=prompt_text,
                        variables_json=json.dumps(case.variables),
                    )
                )
        return rendered

    def _upsert_model_metadata(self, session: Any, model_ids: list[str]) -> dict[str, int | None]:
        """Persist model metadata and return model_id -> metadata_id map."""
        metadata_by_model: dict[str, ModelMetadataRecord] = {}
        try:
            for record in self.client.list_models():
                metadata_by_model[record.model_id] = record
        except OpenRouterClientError as exc:
            logger.warning("Model metadata fetch failed, falling back to minimal metadata: %s", exc)

        id_map: dict[str, int | None] = {}
        for model_id in model_ids:
            existing = session.query(db_models.ModelMetadata).filter_by(model_id=model_id).one_or_none()
            provider = model_id.split("/", maxsplit=1)[0] if "/" in model_id else "unknown"
            fetched = metadata_by_model.get(model_id)

            if existing is None:
                entity = db_models.ModelMetadata(
                    model_id=model_id,
                    display_name=fetched.name if fetched else model_id,
                    provider=provider,
                    context_length=fetched.context_length if fetched else None,
                    input_price_per_million=self._to_float(fetched.prompt_price) if fetched else None,
                    output_price_per_million=self._to_float(fetched.completion_price) if fetched else None,
                    supported_parameters_json=(json.dumps(fetched.raw_payload) if fetched else json.dumps({})),
                )
                session.add(entity)
                session.flush()
                id_map[model_id] = entity.id
            else:
                id_map[model_id] = existing.id

        return id_map

    def _persist_prompts(
        self,
        session: Any,
        run_id: int,
        rendered_cases: list[RenderedPromptCase],
    ) -> dict[str, int]:
        """Persist rendered prompt records and return case_id -> prompt_id map."""
        case_to_prompt_id: dict[str, int] = {}
        for item in rendered_cases:
            prompt_record = db_models.PromptRecord(
                run_id=run_id,
                dimension=item.case.dimension,
                template_name=item.case.template_name,
                template_checksum=item.template_checksum,
                case_id=item.case.case_id,
                rendered_prompt=item.rendered_prompt,
                variables_json=item.variables_json,
            )
            session.add(prompt_record)
            session.flush()
            case_to_prompt_id[item.case.case_id] = prompt_record.id
        return case_to_prompt_id

    def _aggregate_for_report(self, session: Any, run_id: int) -> list[ModelAggregate]:
        """Build model aggregates for HTML reporting from score records."""
        rows = session.query(db_models.ResponseRecord).filter(db_models.ResponseRecord.run_id == run_id).all()
        grouped: dict[str, dict[str, list[float]]] = {}
        for row in rows:
            if not row.model_id or not row.dimension or row.score is None:
                continue
            grouped.setdefault(row.model_id, {}).setdefault(row.dimension, []).append(float(row.score))

        aggregates: list[ModelAggregate] = []
        for model_id, by_dim in grouped.items():
            euphemism_values = by_dim.get("euphemism", [])
            food_values = by_dim.get("food_defaults", [])
            framing_values = by_dim.get("framing_neutrality", [])

            euphemism_score = sum(euphemism_values) / len(euphemism_values) if euphemism_values else 0.0
            food_score = sum(food_values) / len(food_values) if food_values else 0.0
            framing_score = sum(framing_values) / len(framing_values) if framing_values else 0.0
            composite = (euphemism_score + food_score + framing_score) / 3.0

            aggregates.append(
                ModelAggregate(
                    model_id=model_id,
                    euphemism=round(euphemism_score, 2),
                    food_defaults=round(food_score, 2),
                    framing_neutrality=round(framing_score, 2),
                    composite=round(composite, 2),
                )
            )

        aggregates.sort(key=lambda record: record.composite, reverse=True)
        return aggregates

    def _to_float(self, value: str | None) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            return None
