from __future__ import annotations

import json
from pathlib import Path

from data.hashing import content_hash
from llm.base import LLMRequest, LLMResponse


class LLMCallStore:
    """Writes every request and reply to disk once. A path that exists is never rewritten."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._sequence = 0

    def record(self, request: LLMRequest, response: LLMResponse) -> Path:
        self._sequence += 1
        request_payload = request.model_dump(mode="json")
        response_payload = response.model_dump(mode="json")
        record = {
            "sequence": self._sequence,
            "purpose": request.purpose,
            "request": request_payload,
            "request_hash": content_hash(request_payload),
            "response": response_payload,
            "response_hash": content_hash(response.content.encode("utf-8")),
        }
        path = self.root / f"{self._sequence:02d}_{request.purpose or 'call'}.json"
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite LLM call record {path}")
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        return path
