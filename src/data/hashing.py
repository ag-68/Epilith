from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid5, NAMESPACE_URL


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"Cannot serialize {type(value)}")


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=json_default)


def content_hash(payload: Any) -> str:
    if isinstance(payload, bytes):
        return sha256_bytes(payload)
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def stable_id(*parts: str) -> str:
    return str(uuid5(NAMESPACE_URL, "|".join(parts)))
