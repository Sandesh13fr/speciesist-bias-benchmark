"""Tests for prompt template rendering behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from benchmark.runner import render_prompt_template


@pytest.fixture
def templates_dir() -> Path:
    """Return templates root directory."""
    return Path(__file__).resolve().parents[1] / "templates"


def test_all_templates_render_with_valid_context(templates_dir: Path) -> None:
    """All three benchmark templates should render successfully."""
    contexts = {
        "euphemism.j2": {
            "case_id": "EUPH-T1",
            "user_request": "Explain terminology.",
            "context_hint": "Use plain language.",
            "industry_term": "processing",
            "plain_term": "slaughter",
        },
        "food_defaults.j2": {
            "case_id": "FOOD-T1",
            "user_request": "Give meal ideas.",
            "nutrition_goal": "balanced",
            "servings": 2,
            "constraints": "quick prep",
        },
        "framing_neutrality.j2": {
            "case_id": "FRAME-T1",
            "user_request": "Describe impacts.",
            "audience": "students",
            "tone": "neutral",
            "scenario_note": "Include welfare context.",
        },
    }

    for template_name, context in contexts.items():
        rendered = render_prompt_template(templates_dir / template_name, context)
        assert rendered.strip() != ""
        assert f"CASE_ID: {context['case_id']}" in rendered


def test_missing_variable_raises_error(templates_dir: Path) -> None:
    """Rendering with missing required context variable should fail."""
    incomplete_context = {
        "case_id": "EUPH-MISS",
        "user_request": "Explain terminology.",
        "context_hint": "Use plain language.",
        "industry_term": "processing",
        # plain_term intentionally missing
    }

    with pytest.raises(ValueError):
        render_prompt_template(templates_dir / "euphemism.j2", incomplete_context)


def test_rendered_text_non_empty_and_contains_case_metadata(templates_dir: Path) -> None:
    """Rendered template should contain benchmark metadata and non-empty body."""
    context = {
        "case_id": "FRAME-META",
        "user_request": "Explain framing.",
        "audience": "general public",
        "tone": "informative",
        "scenario_note": "Include ethical context.",
    }

    rendered = render_prompt_template(templates_dir / "framing_neutrality.j2", context)

    assert rendered.strip()
    assert "BENCHMARK: Speciesist Bias Benchmark" in rendered
    assert "DIMENSION: Framing Neutrality" in rendered
    assert "CASE_ID: FRAME-META" in rendered
