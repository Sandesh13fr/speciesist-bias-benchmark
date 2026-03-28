"""Tests for SQLite schema and transactional behavior."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import inspect

from database.db import create_engine_and_session, init_db, session_scope
from database.models import BenchmarkRun, PromptRecord, ResponseRecord, ScoreRecord


@pytest.fixture
def database_url(tmp_path) -> str:
    """Return temporary SQLite database URL."""
    db_file = tmp_path / "benchmark_test.db"
    return f"sqlite:///{db_file}"


def test_schema_initialization(database_url: str) -> None:
    """Database initialization should create required schema tables."""
    init_db(database_url)
    engine, _ = create_engine_and_session(database_url)
    table_names = set(inspect(engine).get_table_names())

    assert {"runs", "prompts", "responses", "scores", "model_metadata"}.issubset(table_names)


def test_transactional_session_commit(database_url: str) -> None:
    """session_scope should commit inserts when no exception occurs."""
    init_db(database_url)

    with session_scope(database_url) as session:
        session.add(
            BenchmarkRun(
                run_label="run-commit",
                status="running",
                benchmark_version="1.0.0",
                selected_models_json=json.dumps(["openai/gpt-4o-mini"]),
                selected_dimensions_json=json.dumps(["euphemism"]),
                notes=None,
            )
        )

    with session_scope(database_url) as session:
        rows = session.query(BenchmarkRun).all()
        assert len(rows) == 1
        assert rows[0].run_label == "run-commit"


def test_transactional_rollback_on_exception(database_url: str) -> None:
    """session_scope should roll back inserts when exception is raised."""
    init_db(database_url)

    with pytest.raises(RuntimeError):
        with session_scope(database_url) as session:
            session.add(
                BenchmarkRun(
                    run_label="run-rollback",
                    status="running",
                    benchmark_version="1.0.0",
                    selected_models_json=json.dumps(["openai/gpt-4o-mini"]),
                    selected_dimensions_json=json.dumps(["euphemism"]),
                    notes=None,
                )
            )
            raise RuntimeError("force rollback")

    with session_scope(database_url) as session:
        rows = session.query(BenchmarkRun).all()
        assert rows == []


def test_create_and_retrieve_run_prompt_response_score_rows(database_url: str) -> None:
    """Run, prompt, response, and score rows should persist and be queryable."""
    init_db(database_url)

    with session_scope(database_url) as session:
        run = BenchmarkRun(
            run_label="run-full",
            status="completed",
            benchmark_version="1.0.0",
            selected_models_json=json.dumps(["openai/gpt-4o-mini"]),
            selected_dimensions_json=json.dumps(["euphemism"]),
            notes="test",
        )
        session.add(run)
        session.flush()

        prompt = PromptRecord(
            run_id=run.id,
            dimension="euphemism",
            template_name="euphemism.j2",
            template_checksum="abc123",
            case_id="EUPH-TDB",
            rendered_prompt="Prompt text",
            variables_json=json.dumps({"case_id": "EUPH-TDB"}),
        )
        session.add(prompt)
        session.flush()

        response = ResponseRecord(
            run_id=run.id,
            prompt_id=prompt.id,
            model_metadata_id=None,
            status="completed",
            raw_text="Raw text",
            response_json=json.dumps({"id": "resp_1"}),
            latency_ms=100.0,
            input_tokens=12,
            output_tokens=18,
            error_message=None,
            model_id="openai/gpt-4o-mini",
            dimension="euphemism",
            prompt_name="EUPH-TDB",
            prompt_text="Prompt text",
            response_text="Response text",
            score=8.2,
            rationale="deterministic",
        )
        session.add(response)
        session.flush()

        score = ScoreRecord(
            response_id=response.id,
            dimension="euphemism",
            raw_weighted_score=0.82,
            normalized_score=8.2,
            scorer_version="1.0.0",
            breakdown_json=json.dumps({"lexical_accuracy": {"signal_score": 0.8}}),
        )
        session.add(score)

    with session_scope(database_url) as session:
        stored_run = session.query(BenchmarkRun).filter_by(run_label="run-full").one()
        stored_prompt = session.query(PromptRecord).filter_by(case_id="EUPH-TDB").one()
        stored_response = session.query(ResponseRecord).filter_by(prompt_id=stored_prompt.id).one()
        stored_score = session.query(ScoreRecord).filter_by(response_id=stored_response.id).one()

        assert stored_run.status == "completed"
        assert stored_prompt.dimension == "euphemism"
        assert stored_response.model_id == "openai/gpt-4o-mini"
        assert stored_score.normalized_score == pytest.approx(8.2)
