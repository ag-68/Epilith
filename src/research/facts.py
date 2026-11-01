from __future__ import annotations

import json
from pathlib import Path

from data.config import DATA_DIR, PROJECT_ROOT, company_by_ticker
from data.models import ExperimentReport
from research.models import FactSheet

REPORT_DIR = PROJECT_ROOT / "experiments" / "exp0a" / "output"


def latest_report_for(ticker: str, report_dir: Path = REPORT_DIR) -> tuple[Path, ExperimentReport]:
    """Newest Experiment 0a report that covers the ticker. Full three-company runs are preferred."""
    wanted = ticker.upper()
    candidates: list[tuple[int, str, Path]] = []
    for path in report_dir.glob("report_*.json"):
        tickers = path.stem.split("_")[1:-1]
        if wanted in tickers:
            candidates.append((len(tickers), path.stem.split("_")[-1], path))
    if not candidates:
        raise FileNotFoundError(f"No Experiment 0a report for {wanted} under {report_dir}")
    candidates.sort()
    path = candidates[-1][2]
    report = ExperimentReport.model_validate_json(path.read_text(encoding="utf-8"))
    return path, report


def latest_snapshot_id(ticker: str, normalized_dir: Path | None = None) -> str:
    folder = (normalized_dir or DATA_DIR / "normalized") / ticker.upper()
    newest: tuple[str, str] | None = None
    for path in folder.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        created = payload.get("created_at", "")
        if newest is None or created > newest[0]:
            newest = (created, payload["snapshot_id"])
    if newest is None:
        raise FileNotFoundError(f"No normalized snapshot for {ticker} under {folder}")
    return newest[1]


def load_fact_sheet(ticker: str) -> FactSheet:
    path, report = latest_report_for(ticker)
    validation = next(c for c in report.companies if c.ticker.upper() == ticker.upper())
    if not validation.passed:
        raise RuntimeError(f"{ticker} did not pass Experiment 0a in {path.name}; 0b requires validated facts.")
    company = company_by_ticker(ticker)
    return FactSheet.from_validation(
        validation,
        company_name=company.name,
        listing=company.listing,
        currency=company.valuation_currency,
        data_snapshot_id=latest_snapshot_id(ticker),
        report_path=str(path.relative_to(PROJECT_ROOT)),
        report_generated_at=report.generated_at,
    )
