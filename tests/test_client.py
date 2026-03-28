"""Tests for OpenRouter client using mocked HTTP behavior only."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from tenacity import wait_none

import benchmark.openrouter_client as client_module
from benchmark.openrouter_client import (
    OpenRouterClient,
    OpenRouterHTTPError,
)


@dataclass
class FakeResponse:
    """Simple fake requests.Response for deterministic client tests."""

    status_code: int
    payload: dict
    text: str = ""

    def json(self) -> dict:
        return self.payload


@pytest.fixture
def client() -> OpenRouterClient:
    """Create client instance with retry configuration suitable for tests."""
    return OpenRouterClient(
        api_key="test-key",
        base_url="https://openrouter.ai/api/v1",
        timeout_seconds=10,
        max_retries=3,
        requests_per_minute=60000,
        app_name="test-suite",
        site_url="https://example.org",
    )


def test_completion_normalization_from_mocked_payload(client: OpenRouterClient) -> None:
    """normalize_completion should extract content, usage, and metadata deterministically."""
    payload = {
        "id": "gen_123",
        "model": "openai/gpt-4o-mini",
        "created": 1712345678,
        "usage": {"prompt_tokens": 11, "completion_tokens": 22, "total_tokens": 33},
        "choices": [
            {
                "message": {"content": "Synthetic completion text"},
                "finish_reason": "stop",
            }
        ],
    }

    normalized = client.normalize_completion(payload, model="openai/gpt-4o-mini")

    assert normalized.content == "Synthetic completion text"
    assert normalized.model == "openai/gpt-4o-mini"
    assert normalized.usage.prompt_tokens == 11
    assert normalized.usage.completion_tokens == 22
    assert normalized.usage.total_tokens == 33
    assert normalized.finish_reason == "stop"


def test_non_retriable_400_failure(monkeypatch: pytest.MonkeyPatch, client: OpenRouterClient) -> None:
    """HTTP 400 should raise immediately without retry attempts."""
    calls: list[str] = []

    def fake_request(**kwargs):
        calls.append("called")
        return FakeResponse(status_code=400, payload={"error": "bad request"}, text="bad request")

    monkeypatch.setattr(client_module.requests, "request", fake_request)

    with pytest.raises(OpenRouterHTTPError) as exc_info:
        client.chat_completion(
            model="openai/gpt-4o-mini",
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.2,
            max_tokens=20,
        )

    assert exc_info.value.status_code == 400
    assert len(calls) == 1


def test_retriable_429_or_500_behavior(monkeypatch: pytest.MonkeyPatch, client: OpenRouterClient) -> None:
    """Retriable server/rate-limit errors should retry and then succeed when response recovers."""
    responses = [
        FakeResponse(status_code=429, payload={"error": "rate limited"}, text="rate limited"),
        FakeResponse(
            status_code=200,
            payload={
                "model": "openai/gpt-4o-mini",
                "choices": [{"message": {"content": "Recovered"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
            },
        ),
    ]

    call_count = {"count": 0}

    def fake_request(**kwargs):
        del kwargs
        current = responses[call_count["count"]]
        call_count["count"] += 1
        return current

    monkeypatch.setattr(client_module.requests, "request", fake_request)
    monkeypatch.setattr(client_module, "wait_exponential", lambda **_: wait_none())

    normalized = client.chat_completion(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": "hello"}],
        temperature=0.2,
        max_tokens=20,
    )

    assert normalized.content == "Recovered"
    assert call_count["count"] == 2


def test_model_metadata_parsing_from_list_models_payload(
    monkeypatch: pytest.MonkeyPatch,
    client: OpenRouterClient,
) -> None:
    """list_models should parse valid model metadata entries and skip invalid ones."""
    payload = {
        "data": [
            {
                "id": "openai/gpt-4o-mini",
                "name": "GPT-4o mini",
                "context_length": 128000,
                "pricing": {"prompt": "0.15", "completion": "0.60"},
            },
            {
                "id": "anthropic/claude-3-haiku",
                "name": "Claude 3 Haiku",
                "context_length": 200000,
                "pricing": {"prompt": "0.25", "completion": "1.25"},
            },
            {"name": "invalid-no-id"},
        ]
    }

    def fake_request(**kwargs):
        del kwargs
        return FakeResponse(status_code=200, payload=payload)

    monkeypatch.setattr(client_module.requests, "request", fake_request)

    models = client.list_models()

    assert len(models) == 2
    assert models[0].model_id == "openai/gpt-4o-mini"
    assert models[0].context_length == 128000
    assert models[0].prompt_price == "0.15"
    assert models[1].model_id == "anthropic/claude-3-haiku"
