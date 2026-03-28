"""Robust OpenRouter API client with normalization, retries, and rate limiting."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import requests
from tenacity import RetryCallState, Retrying, retry_if_exception, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class OpenRouterClientError(Exception):
    """Base exception for OpenRouter client failures."""


class OpenRouterHTTPError(OpenRouterClientError):
    """HTTP-level OpenRouter failure with status and response context."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_text: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class OpenRouterResponseError(OpenRouterClientError):
    """OpenRouter response parsing or schema validation failure."""


@dataclass(frozen=True)
class NormalizedUsage:
    """Normalized usage tokens from OpenRouter completion payload."""

    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None


@dataclass(frozen=True)
class NormalizedCompletion:
    """Normalized completion result for downstream benchmark logic."""

    model: str
    content: str
    usage: NormalizedUsage
    raw_payload: dict[str, Any]
    completion_id: str | None
    finish_reason: str | None
    created: int | None


@dataclass(frozen=True)
class ModelMetadataRecord:
    """Normalized OpenRouter model metadata record."""

    model_id: str
    name: str | None
    context_length: int | None
    prompt_price: str | None
    completion_price: str | None
    raw_payload: dict[str, Any]


def build_user_message(prompt_text: str) -> list[dict[str, str]]:
    """Build a minimal OpenAI-compatible user message list.

    Args:
        prompt_text: Prompt text content.

    Returns:
        List containing one user message.
    """
    return [{"role": "user", "content": prompt_text}]


class OpenRouterClient:
    """OpenRouter API client with retries, normalization, and audit-friendly payloads.

    Args:
        api_key: OpenRouter API key.
        base_url: OpenRouter base URL.
        timeout_seconds: Request timeout in seconds.
        max_retries: Maximum number of retry attempts.
        requests_per_minute: Client-side request rate limit.
        app_name: Optional app attribution header.
        site_url: Optional site URL attribution header.
        rate_limit_rpm: Deprecated alias for requests_per_minute.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout_seconds: int = 60,
        max_retries: int = 5,
        requests_per_minute: int = 30,
        app_name: str | None = None,
        site_url: str | None = None,
        rate_limit_rpm: int | None = None,
    ) -> None:
        if not api_key.strip():
            raise OpenRouterClientError("OpenRouter API key must not be empty")
        if timeout_seconds <= 0:
            raise OpenRouterClientError("timeout_seconds must be greater than 0")

        effective_rpm = rate_limit_rpm if rate_limit_rpm is not None else requests_per_minute
        if effective_rpm <= 0:
            raise OpenRouterClientError("requests_per_minute must be greater than 0")

        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._max_retries = max(1, max_retries)
        self._min_interval_seconds = 60.0 / effective_rpm
        self._last_request_time = 0.0

        self._headers: dict[str, str] = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if app_name:
            self._headers["X-Title"] = app_name
        if site_url:
            self._headers["HTTP-Referer"] = site_url

    def list_models(self) -> list[ModelMetadataRecord]:
        """Return normalized model metadata records from OpenRouter.

        Returns:
            List of model metadata entries.
        """
        payload = self._request_json("GET", "/models")
        records = payload.get("data")
        if not isinstance(records, list):
            raise OpenRouterResponseError("OpenRouter /models response missing 'data' list")

        models: list[ModelMetadataRecord] = []
        for item in records:
            if not isinstance(item, dict):
                continue

            pricing = item.get("pricing") if isinstance(item.get("pricing"), dict) else {}
            context_length = item.get("context_length")
            context_length_int = context_length if isinstance(context_length, int) else None

            model_id = item.get("id")
            if not isinstance(model_id, str) or not model_id.strip():
                continue

            models.append(
                ModelMetadataRecord(
                    model_id=model_id,
                    name=item.get("name") if isinstance(item.get("name"), str) else None,
                    context_length=context_length_int,
                    prompt_price=pricing.get("prompt") if isinstance(pricing.get("prompt"), str) else None,
                    completion_price=(
                        pricing.get("completion") if isinstance(pricing.get("completion"), str) else None
                    ),
                    raw_payload=item,
                )
            )

        return models

    def chat_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 350,
    ) -> NormalizedCompletion:
        """Create a chat completion and return normalized output.

        Args:
            model: OpenRouter model ID.
            messages: OpenAI-compatible message list.
            temperature: Sampling temperature.
            max_tokens: Output token cap.

        Returns:
            Normalized completion object.
        """
        if not model.strip():
            raise OpenRouterClientError("Model must not be empty")
        if not messages:
            raise OpenRouterClientError("messages must not be empty")

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        raw = self._post(payload)
        return self.normalize_completion(raw, model=model)

    def normalize_completion(self, payload: dict[str, Any], model: str) -> NormalizedCompletion:
        """Normalize OpenRouter chat-completion payload.

        Args:
            payload: Raw OpenRouter response payload.
            model: Requested model ID.

        Returns:
            Normalized completion object.
        """
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise OpenRouterResponseError("Completion payload missing non-empty 'choices' list")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise OpenRouterResponseError("First completion choice is not an object")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise OpenRouterResponseError("Completion choice missing 'message' object")

        content = self._extract_message_content(message)

        usage_obj = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        usage = NormalizedUsage(
            prompt_tokens=self._to_optional_int(usage_obj.get("prompt_tokens")),
            completion_tokens=self._to_optional_int(usage_obj.get("completion_tokens")),
            total_tokens=self._to_optional_int(usage_obj.get("total_tokens")),
        )

        response_model = payload.get("model") if isinstance(payload.get("model"), str) else model

        return NormalizedCompletion(
            model=response_model,
            content=content,
            usage=usage,
            raw_payload=payload,
            completion_id=payload.get("id") if isinstance(payload.get("id"), str) else None,
            finish_reason=(
                first_choice.get("finish_reason") if isinstance(first_choice.get("finish_reason"), str) else None
            ),
            created=self._to_optional_int(payload.get("created")),
        )

    def generate(
        self,
        model_id: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Backward-compatible text generation helper.

        Args:
            model_id: Model identifier.
            prompt: Prompt text.
            temperature: Sampling temperature.
            max_tokens: Output token limit.

        Returns:
            Completion text.
        """
        completion = self.chat_completion(
            model=model_id,
            messages=build_user_message(prompt),
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return completion.content

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Backward-compatible chat-completion POST helper for tests/callers."""
        return self._request_json("POST", "/chat/completions", json_payload=payload)

    def _request_json(
        self,
        method: str,
        endpoint: str,
        json_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send an HTTP request with retries and return parsed JSON payload."""

        def _retryable(exc: BaseException) -> bool:
            if isinstance(exc, OpenRouterHTTPError):
                return exc.status_code == 429 or (exc.status_code is not None and exc.status_code >= 500)
            if isinstance(exc, requests.RequestException):
                return True
            return False

        retrying = Retrying(
            reraise=True,
            retry=retry_if_exception(_retryable),
            wait=wait_exponential(multiplier=1, min=1, max=15),
            stop=stop_after_attempt(self._max_retries),
            after=self._log_retry,
        )

        for attempt in retrying:
            with attempt:
                self._throttle()
                url = f"{self._base_url}{endpoint}"
                try:
                    response = requests.request(
                        method=method,
                        url=url,
                        headers=self._headers,
                        json=json_payload,
                        timeout=self._timeout_seconds,
                    )
                except requests.RequestException as exc:
                    raise OpenRouterClientError(f"OpenRouter request failed: {exc}") from exc

                if response.status_code >= 400:
                    self._raise_http_error(response=response, endpoint=endpoint)

                try:
                    payload = response.json()
                except ValueError as exc:
                    raise OpenRouterResponseError(
                        f"OpenRouter returned invalid JSON for {endpoint}: {response.text[:300]}"
                    ) from exc

                if not isinstance(payload, dict):
                    raise OpenRouterResponseError(
                        f"OpenRouter returned non-object JSON payload for {endpoint}"
                    )

                return payload

        raise OpenRouterClientError("OpenRouter request failed after retries")

    def _raise_http_error(self, response: requests.Response, endpoint: str) -> None:
        """Raise typed HTTP errors with retry policy semantics."""
        status_code = response.status_code
        body_preview = response.text[:400]

        message = f"OpenRouter HTTP {status_code} for {endpoint}: {body_preview}"

        if status_code in {400, 401, 403, 404}:
            raise OpenRouterHTTPError(
                message,
                status_code=status_code,
                response_text=body_preview,
            )

        if status_code == 429 or status_code >= 500:
            raise OpenRouterHTTPError(
                message,
                status_code=status_code,
                response_text=body_preview,
            )

        raise OpenRouterHTTPError(
            message,
            status_code=status_code,
            response_text=body_preview,
        )

    def _throttle(self) -> None:
        """Apply basic client-side rate limiting."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval_seconds:
            sleep_seconds = self._min_interval_seconds - elapsed
            logger.debug("Rate limiting request; sleeping %.3f seconds", sleep_seconds)
            time.sleep(sleep_seconds)
        self._last_request_time = time.monotonic()

    def _extract_message_content(self, message: dict[str, Any]) -> str:
        """Normalize message content to a single text field."""
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text_value = item.get("text")
                    if isinstance(text_value, str):
                        parts.append(text_value)
            normalized = "\n".join(parts).strip()
            if normalized:
                return normalized

        raise OpenRouterResponseError("Completion message content is missing or not text")

    def _to_optional_int(self, value: Any) -> int | None:
        """Safely parse optional integer value."""
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return None

    def _log_retry(self, retry_state: RetryCallState) -> None:
        """Log retry attempts for observability."""
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        logger.warning(
            "Retrying OpenRouter request (attempt %s/%s) due to: %s",
            retry_state.attempt_number,
            self._max_retries,
            exc,
        )
