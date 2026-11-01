from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from llm.base import LLMRequest, LLMResponse


class ScriptedProvider:
    """Replays prepared replies keyed by request purpose. For tests and dry runs; no network."""

    name = "scripted"

    def __init__(self, replies: dict[str, Any]) -> None:
        self.replies = replies
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if request.purpose not in self.replies:
            raise KeyError(f"No scripted reply for purpose {request.purpose!r}")
        reply = self.replies[request.purpose]
        content = reply if isinstance(reply, str) else json.dumps(reply)
        now = datetime.now(timezone.utc)
        return LLMResponse(
            provider=self.name,
            model=request.model,
            model_version="scripted",
            content=content,
            requested_at=now,
            received_at=now,
        )
