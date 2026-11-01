from __future__ import annotations

import os
import time
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
    ) -> None:
        self.api_key = (api_key or os.getenv(api_key_env, "")).strip()
        if not self.api_key:
            raise RuntimeError(f"{api_key_env} is not set. Add it to .env locally or as a Runtime Secret for cloud agents.")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_attempts = max_attempts
        self._transport = transport

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
        with httpx.Client(timeout=self.timeout, transport=self._transport) as client:
            for attempt in range(1, self.max_attempts + 1):
                try:
                    response = client.post(f"{self.base_url}/chat/completions", json=body, headers=headers)
                except httpx.TransportError as exc:
                    last_error = exc
                else:
                    if response.status_code not in RETRY_STATUSES:
                        if response.is_error:
                            # Keep Groq's own message; the bare status code hides the reason (limits, model names).
                            raise RuntimeError(
                                f"Groq refused the {request.purpose} call for {request.model} "
                                f"({response.status_code}): {_error_message(response)}"
                            )
                        return self._parse(request, response.json(), requested_at)
                    last_error = httpx.HTTPStatusError(
                        f"Groq returned {response.status_code}: {response.text[:300]}",
                        request=response.request,
                        response=response,
                    )
                if attempt < self.max_attempts:
                    time.sleep(2**attempt)
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


def _error_message(response: httpx.Response) -> str:
    try:
        return str(response.json()["error"]["message"])
    except (ValueError, KeyError, TypeError):
        return response.text[:500]
