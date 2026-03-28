"""Data access functions for benchmark persistence."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import BenchmarkRun, ModelMetadata, PromptResult


@dataclass(frozen=True)
class PromptResultRecord:
    """In-memory representation of a prompt result before persistence.

    Attributes:
        model_id: Model identifier.
        dimension: Benchmark dimension name.
        prompt_name: Prompt item identifier.
        prompt_text: Fully rendered prompt text.
        response_text: Model response text.
        score: Deterministic score from 0.0 to 10.0.
        rationale: Explainable rubric rationale.
    """

    model_id: str
    dimension: str
    prompt_name: str
    prompt_text: str
    response_text: str
    score: float
    rationale: str


def upsert_model_metadata(session: Session, model_id: str) -> None:
    """Insert model metadata when missing.

    Args:
        session: Active SQLAlchemy session.
        model_id: Model identifier.
    """
    existing = session.execute(
        select(ModelMetadata).where(ModelMetadata.model_id == model_id)
    ).scalar_one_or_none()
    if existing is None:
        provider = model_id.split("/", maxsplit=1)[0] if "/" in model_id else "unknown"
        session.add(ModelMetadata(model_id=model_id, provider=provider))


def create_run(
    session: Session,
    run_uuid: str,
    requested_models: list[str],
    requested_dimensions: list[str],
    status: str,
) -> BenchmarkRun:
    """Create a benchmark run record.

    Args:
        session: Active SQLAlchemy session.
        run_uuid: Public run UUID.
        requested_models: Requested model IDs.
        requested_dimensions: Requested benchmark dimensions.
        status: Initial status string.

    Returns:
        Created BenchmarkRun ORM instance.
    """
    run = BenchmarkRun(
        run_uuid=run_uuid,
        requested_models=",".join(requested_models),
        requested_dimensions=",".join(requested_dimensions),
        status=status,
    )
    session.add(run)
    session.flush()
    return run


def update_run_status(session: Session, run_id: int, status: str) -> None:
    """Update run status.

    Args:
        session: Active SQLAlchemy session.
        run_id: Internal run primary key.
        status: New status string.
    """
    run = session.get(BenchmarkRun, run_id)
    if run is None:
        raise ValueError(f"Benchmark run {run_id} not found")
    run.status = status


def insert_prompt_results(
    session: Session,
    run_id: int,
    records: list[PromptResultRecord],
) -> None:
    """Persist prompt results for a run.

    Args:
        session: Active SQLAlchemy session.
        run_id: Internal run primary key.
        records: Prompt result records.
    """
    entities = [
        PromptResult(
            run_id=run_id,
            model_id=record.model_id,
            dimension=record.dimension,
            prompt_name=record.prompt_name,
            prompt_text=record.prompt_text,
            response_text=record.response_text,
            score=record.score,
            rationale=record.rationale,
        )
        for record in records
    ]
    session.add_all(entities)
