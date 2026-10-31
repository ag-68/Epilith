from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from data.models import Company

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected mapping in {path}")
    return loaded


def load_companies(path: Path | None = None) -> list[Company]:
    raw = load_yaml(path or CONFIG_DIR / "companies.yaml")
    return [Company.model_validate(item) for item in raw["companies"]]


def company_by_ticker(ticker: str, path: Path | None = None) -> Company:
    wanted = ticker.upper()
    for company in load_companies(path):
        if company.ticker.upper() == wanted:
            return company
    raise KeyError(f"Unknown ticker {ticker}")


def load_xbrl_concepts(path: Path | None = None) -> dict[str, Any]:
    return load_yaml(path or CONFIG_DIR / "xbrl_concepts.yaml")
