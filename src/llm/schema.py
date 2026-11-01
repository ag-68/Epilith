from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    """JSON schema for constrained decoding: every property required, nothing extra.

    Strict structured output needs ``required`` to list every property and
    ``additionalProperties`` to be false on every object, including nested ones.
    Defaults are dropped because strict mode rejects them.
    """
    schema = model.model_json_schema()
    _tighten(schema)
    return schema


def _tighten(node: Any) -> None:
    if isinstance(node, dict):
        if node.get("type") == "object" and isinstance(node.get("properties"), dict):
            node["required"] = list(node["properties"].keys())
            node["additionalProperties"] = False
        node.pop("default", None)
        for value in node.values():
            _tighten(value)
    elif isinstance(node, list):
        for item in node:
            _tighten(item)
