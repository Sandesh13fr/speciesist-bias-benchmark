"""SQLAlchemy ORM schema for benchmark runs, prompts, responses, scores, and model metadata."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, synonym


def utc_now() -> datetime:
    """Return timezone-aware current UTC timestamp."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Base declarative class for SQLAlchemy ORM models."""


class BenchmarkRun(Base):
    """Benchmark run metadata and lifecycle state."""

    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_label: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    benchmark_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    selected_models_json: Mapped[str] = mapped_column(Text, nullable=False)
    selected_dimensions_json: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    prompts: Mapped[list[PromptRecord]] = relationship(back_populates="run", cascade="all, delete-orphan")
    responses: Mapped[list[ResponseRecord]] = relationship(back_populates="run", cascade="all, delete-orphan")

    # Compatibility aliases for older callsites.
    run_uuid = synonym("run_label")
    requested_models = synonym("selected_models_json")
    requested_dimensions = synonym("selected_dimensions_json")


class PromptRecord(Base):
    """Rendered prompt record for one benchmark case."""

    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False, index=True)
    dimension: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    template_name: Mapped[str] = mapped_column(String(128), nullable=False)
    template_checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    case_id: Mapped[str] = mapped_column(String(128), nullable=False)
    rendered_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    variables_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    run: Mapped[BenchmarkRun] = relationship(back_populates="prompts")
    responses: Mapped[list[ResponseRecord]] = relationship(back_populates="prompt", cascade="all, delete-orphan")


class ModelMetadata(Base):
    """Model metadata snapshot from model catalog API."""

    __tablename__ = "model_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(120), nullable=True)
    context_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_price_per_million: Mapped[float | None] = mapped_column(Float, nullable=True)
    output_price_per_million: Mapped[float | None] = mapped_column(Float, nullable=True)
    supported_parameters_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    responses: Mapped[list[ResponseRecord]] = relationship(back_populates="model_metadata")


class ResponseRecord(Base):
    """Raw model response payload and status for one prompt invocation."""

    __tablename__ = "responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False, index=True)
    prompt_id: Mapped[int | None] = mapped_column(ForeignKey("prompts.id"), nullable=True, index=True)
    model_metadata_id: Mapped[int | None] = mapped_column(
        ForeignKey("model_metadata.id"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(40), default="completed", nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Compatibility fields for current repository pipeline.
    model_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    dimension: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    prompt_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    prompt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped[BenchmarkRun] = relationship(back_populates="responses")
    prompt: Mapped[PromptRecord | None] = relationship(back_populates="responses")
    model_metadata: Mapped[ModelMetadata | None] = relationship(back_populates="responses")
    scores: Mapped[list[ScoreRecord]] = relationship(back_populates="response", cascade="all, delete-orphan")


class ScoreRecord(Base):
    """Deterministic scoring output for a response."""

    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    response_id: Mapped[int] = mapped_column(ForeignKey("responses.id"), nullable=False, index=True)
    dimension: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    raw_weighted_score: Mapped[float] = mapped_column(Float, nullable=False)
    normalized_score: Mapped[float] = mapped_column(Float, nullable=False)
    scorer_version: Mapped[str] = mapped_column(String(40), nullable=False)
    breakdown_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    response: Mapped[ResponseRecord] = relationship(back_populates="scores")


# Compatibility alias expected by existing repository code.
PromptResult = ResponseRecord
