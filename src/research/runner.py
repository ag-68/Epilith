"""Shared path from a typed company name to a memo. Used by the CLI and the local page."""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from pathlib import Path

import yaml

from data.config import DATA_DIR, PROJECT_ROOT
from data.models import Company
from data.registry import CompanyRegistry, _norm
from data.snapshots import SnapshotStore
from decision_log.log import DecisionLog, UserAction, UserActionKind
from llm.config import build_provider, load_llm_config
from research.auto_sources import SourcesUnavailable, build_source_bundle
from research.facts import load_fact_sheet
from research.models import ResearchRun, SourceBundle
from research.pipeline import ResearchPipeline
from research.sources import MANIFEST_NAME, load_source_bundle

SOURCES_DIR = PROJECT_ROOT / "experiments" / "exp0b" / "sources"
AUTO_SOURCES_DIR = DATA_DIR / "sources"
RESEARCH_DIR = DATA_DIR / "research"
DECISION_LOG_DIR = DATA_DIR / "decision_log"

Log = Callable[[str], None]


def ensure_fact_sheet(ticker: str, log: Log = print):
    """Use the newest data-check report for the ticker. If there is none, run the data check now."""
    try:
        return load_fact_sheet(ticker)
    except FileNotFoundError:
        log(f"No Experiment 0a report for {ticker}. Running the data check first.")
    spec = importlib.util.spec_from_file_location("exp0a_run", PROJECT_ROOT / "experiments" / "exp0a" / "run.py")
    exp0a = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(exp0a)
    report, json_path, _ = exp0a.run_and_write([ticker])
    company = report.companies[0]
    log(f"Data check wrote {json_path}: {company.valid_count}/12 valid.")
    if not company.passed:
        raise RuntimeError(
            f"{ticker} failed the data check ({company.valid_count}/12). No memo is written on unvalidated numbers. "
            f"Read {json_path.with_suffix('.md')} and fix the data layer first."
        )
    return load_fact_sheet(ticker)


def ensure_source_bundle(company: Company, log: Log = print) -> SourceBundle:
    """Hand-picked excerpts win when a folder lists some. Otherwise cut the filings automatically."""
    manual = SOURCES_DIR / company.ticker
    manifest = manual / MANIFEST_NAME
    if manifest.exists() and (yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}).get("sources"):
        log(f"Using hand-picked excerpts from {manual}")
        return load_source_bundle(manual, company.ticker)
    try:
        bundle, folder = build_source_bundle(company, SnapshotStore(DATA_DIR), AUTO_SOURCES_DIR)
    except SourcesUnavailable as exc:
        raise RuntimeError(str(exc)) from exc
    log(f"Reading material: {len(bundle.excerpts)} sections from the company's filings, stored in {folder}")
    for excerpt in bundle.excerpts:
        log(f"  - {excerpt.title} ({len(excerpt.text):,} characters)")
    return bundle


def run_memo(query: str, log: Log = print) -> tuple[ResearchRun, str]:
    company = CompanyRegistry().resolve(query)
    ticker = company.ticker
    if _norm(query) != _norm(ticker):
        log(f"{query} -> {company.name} ({company.listing})")
    log("Checking the validated facts…")
    sheet = ensure_fact_sheet(ticker, log)
    log("Preparing the reading material…")
    bundle = ensure_source_bundle(company, log)
    log("Writing the memo (this waits for the model and may take several minutes)…")
    config = load_llm_config()
    provider = build_provider(config)
    pipeline = ResearchPipeline(provider, config, RESEARCH_DIR)
    result = pipeline.run(sheet, bundle)
    entry = DecisionLog(DECISION_LOG_DIR).append(result)
    log(f"Memo written. Decision log entry: {entry.entry_id}")
    log(f"Verified evidence: {len(result.evidence.verified)}; failed quote check: {len(result.evidence.unverified)}")
    log(f"Figures not traceable to the fact sheet: {len(result.number_findings)}")
    for note in result.notes:
        log(f"Note: {note}")
    return result, entry.entry_id


def record_action(entry_id: str, action: UserActionKind, reason: str, notes: str | None = None) -> UserAction:
    return DecisionLog(DECISION_LOG_DIR).record_user_action(entry_id, action, reason, notes)


def list_entries():
    return list(reversed(DecisionLog(DECISION_LOG_DIR).entries()))


def load_entry(entry_id: str):
    return DecisionLog(DECISION_LOG_DIR).read(entry_id)


def memo_markdown(entry_id: str) -> str:
    entry, _ = load_entry(entry_id)
    return Path(entry.memo_path).read_text(encoding="utf-8")
