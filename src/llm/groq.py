from __future__ import annotations

import json
import os
import time
from collections import deque
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import httpx

from llm.base import LLMRequest, LLMResponse

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Models documented by Groq as supporting constrained decoding (strict JSON schema).
STRICT_SCHEMA_MODELS = {
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "meta-models/muse-spark-open",
}

RETRY_STATUSES = {429, 500, 502, 503, 504}


class GroqProvider:
    """Groq's OpenAI-compatible chat endpoint. The only file that knows Groq's wire format."""

    name = "groq"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        api_key_env: str = "GROQ_API_KEY",
        base_url: str = GROQ_BASE_URL,
        timeout: float = 120.0,
        max_attempts: int = 3,
        transport: httpx.BaseTransport | None = None,
        tokens_per_minute: int | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.api_key = (api_key or os.getenv(api_key_env, "")).strip()
        if not self.api_key:
            raise RuntimeError(f"{api_key_env} is not set. Add it to .env locally or as a Runtime Secret for cloud agents.")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_attempts = max_attempts
        self._transport = transport
        self._pacer = TokenPacer(tokens_per_minute, sleep=sleep, clock=clock) if tokens_per_minute else None
        self._sleep = sleep

    def build_body(self, request: LLMRequest) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": request.model,
            "messages": [message.model_dump() for message in request.messages],
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            body["max_completion_tokens"] = request.max_tokens
        if request.json_schema is not None:
            if request.model in STRICT_SCHEMA_MODELS:
                body["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {"name": request.schema_name, "schema": request.json_schema, "strict": True},
                }
            else:
                body["response_format"] = {"type": "json_object"}
        return body

    def complete(self, request: LLMRequest) -> LLMResponse:
        body = self.build_body(request)
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        requested_at = datetime.now(timezone.utc)
        last_error: Exception | None = None
        estimate = estimate_tokens(body)
        with httpx.Client(timeout=self.timeout, transport=self._transport) as client:
            for attempt in range(1, self.max_attempts + 1):
                if self._pacer:
                    self._pacer.wait_for(estimate)
                wait = float(2**attempt)
                try:
                    response = client.post(f"{self.base_url}/chat/completions", json=body, headers=headers)
                except httpx.TransportError as exc:
                    last_error = exc
                else:
                    wait = _retry_after(response, wait)
                    if response.status_code not in RETRY_STATUSES:
                        if response.is_error:
                            # Keep Groq's own message; the bare status code hides the reason (limits, model names).
                            raise RuntimeError(
                                f"Groq refused the {request.purpose} call for {request.model} "
                                f"({response.status_code}): {_error_message(response)}"
                            )
                        parsed = self._parse(request, response.json(), requested_at)
                        if self._pacer:
                            self._pacer.record((parsed.prompt_tokens or 0) + (parsed.completion_tokens or 0) or estimate)
                        return parsed
                    last_error = httpx.HTTPStatusError(
                        f"Groq returned {response.status_code}: {_error_message(response)}",
                        request=response.request,
                        response=response,
                    )
                if attempt < self.max_attempts:
                    self._sleep(wait)
        assert last_error is not None
        raise last_error

    def _parse(self, request: LLMRequest, payload: dict[str, Any], requested_at: datetime) -> LLMResponse:
        choice = payload["choices"][0]
        usage = payload.get("usage") or {}
        return LLMResponse(
            provider=self.name,
            model=request.model,
            model_version=payload.get("system_fingerprint") or payload.get("model"),
            content=choice["message"]["content"] or "",
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            finish_reason=choice.get("finish_reason"),
            requested_at=requested_at,
            received_at=datetime.now(timezone.utc),
            raw=payload,
        )


class TokenPacer:
    """Keeps calls under a tokens-per-minute budget by waiting, not by failing.

    Groq's free tier allows a fixed number of tokens per rolling minute per model. The pacer remembers what
    each call used and, before the next one, sleeps until the estimated request fits in the window.
    """

    def __init__(self, tokens_per_minute: int, *, sleep: Callable[[float], None], clock: Callable[[], float]) -> None:
        self.limit = tokens_per_minute
        self._sleep = sleep
        self._clock = clock
        self._used: deque[tuple[float, int]] = deque()

    def _trim(self, now: float) -> None:
        while self._used and now - self._used[0][0] >= 60:
            self._used.popleft()

    def wait_for(self, tokens: int) -> None:
        if tokens > self.limit:
            raise RuntimeError(
                f"A single request of about {tokens} tokens cannot fit a {self.limit} tokens-per-minute budget. "
                "Shorten the sections or raise the budget."
            )
        while True:
            now = self._clock()
            self._trim(now)
            in_window = sum(used for _, used in self._used)
            if in_window + tokens <= self.limit:
                return
            self._sleep(60 - (now - self._used[0][0]) + 0.5)

    def record(self, tokens: int) -> None:
        self._used.append((self._clock(), tokens))


def estimate_tokens(body: dict[str, Any]) -> int:
    """Rough upper estimate: one token per 3.5 characters of the serialized request."""
    return int(len(json.dumps(body)) / 3.5) + 1


def _retry_after(response: httpx.Response, default: float) -> float:
    header = response.headers.get("retry-after")
    if header:
        try:
            return max(float(header), 0.5)
        except ValueError:
            pass
    return default


def _error_message(response: httpx.Response) -> str:
    try:
        return str(response.json()["error"]["message"])
    except (ValueError, KeyError, TypeError):
        return response.text[:500]
