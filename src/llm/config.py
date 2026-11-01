from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from data.config import CONFIG_DIR, load_yaml
from llm.base import LLMProvider


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    api_key_env: str
    evidence_model: str
    analyst_model: str
    red_team_model: str
    temperature: float = 0.2
    max_tokens: int | None = None
    tokens_per_minute: int | None = None


def load_llm_config(path: Path | None = None) -> LLMConfig:
    return LLMConfig.model_validate(load_yaml(path or CONFIG_DIR / "llm.yaml"))


def build_provider(config: LLMConfig) -> LLMProvider:
    if config.provider == "groq":
        from llm.groq import GroqProvider

        return GroqProvider(api_key_env=config.api_key_env, tokens_per_minute=config.tokens_per_minute)
    raise ValueError(f"Unknown LLM provider {config.provider!r}")
