from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["system", "user", "assistant"]
    content: str


class LLMRequest(BaseModel):
    """Provider-neutral request. The JSON schema, when given, constrains the reply."""

    model_config = ConfigDict(extra="forbid")

    model: str
    messages: list[ChatMessage]
    json_schema: dict[str, Any] | None = None
    schema_name: str = "reply"
    temperature: float = 0.2
    max_tokens: int | None = None
    purpose: str = ""


class LLMResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str
    model_version: str | None = None
    content: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    finish_reason: str | None = None
    requested_at: datetime
    received_at: datetime
    raw: dict[str, Any] = Field(default_factory=dict)


class LLMProvider(Protocol):
    name: str

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Send one chat request and return the reply text with usage metadata."""
