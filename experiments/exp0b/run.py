from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")

import yaml  # noqa: E402

from data.config import DATA_DIR  # noqa: E402
from data.models import Company  # noqa: E402
from data.registry import CompanyRegistry, _norm  # noqa: E402
from data.snapshots import SnapshotStore  # noqa: E402
from decision_log.log import DecisionLog  # noqa: E402
from llm.config import build_provider, load_llm_config  # noqa: E402
from research.auto_sources import SourcesUnavailable, build_source_bundle  # noqa: E402
from research.facts import load_fact_sheet  # noqa: E402
from research.models import SourceBundle  # noqa: E402
from research.pipeline import ResearchPipeline  # noqa: E402
from research.sources import MANIFEST_NAME, load_source_bundle  # noqa: E402

SOURCES_DIR = ROOT / "experiments" / "exp0b" / "sources"
AUTO_SOURCES_DIR = DATA_DIR / "sources"
RESEARCH_DIR = DATA_DIR / "research"
DECISION_LOG_DIR = DATA_DIR / "decision_log"


def ensure_fact_sheet(ticker: str):
    """Use the newest data-check report for the ticker. If there is none, run the data check now."""
    try:
        return load_fact_sheet(ticker)
    except FileNotFoundError:
        print(f"No Experiment 0a report for {ticker}. Running the data check first.")
    spec = importlib.util.spec_from_file_location("exp0a_run", ROOT / "experiments" / "exp0a" / "run.py")
    exp0a = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(exp0a)
    report, json_path, _ = exp0a.run_and_write([ticker])
    company = report.companies[0]
    print(f"Data check wrote {json_path}: {company.valid_count}/12 valid.")
    if not company.passed:
        raise SystemExit(
            f"{ticker} failed the data check ({company.valid_count}/12). No memo is written on unvalidated numbers. "
            f"Read {json_path.with_suffix('.md')} and fix the data layer first."
        )
    return load_fact_sheet(ticker)


def ensure_source_bundle(company: Company) -> SourceBundle:
    """Hand-picked excerpts win when a folder lists some. Otherwise cut the filings automatically."""
    manual = SOURCES_DIR / company.ticker
    manifest = manual / MANIFEST_NAME
    if manifest.exists() and (yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}).get("sources"):
        print(f"Using hand-picked excerpts from {manual}")
        return load_source_bundle(manual, company.ticker)
    try:
        bundle, folder = build_source_bundle(company, SnapshotStore(DATA_DIR), AUTO_SOURCES_DIR)
    except SourcesUnavailable as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Reading material: {len(bundle.excerpts)} sections from the company's filings, stored in {folder}")
    for excerpt in bundle.excerpts:
        print(f"  - {excerpt.title} ({len(excerpt.text):,} characters)")
    return bundle


def run_memo(query: str) -> int:
    company = CompanyRegistry().resolve(query)
    ticker = company.ticker
    if _norm(query) != _norm(ticker):
        print(f"{query} -> {company.name} ({company.listing})")
    sheet = ensure_fact_sheet(ticker)
    bundle = ensure_source_bundle(company)
    config = load_llm_config()
    provider = build_provider(config)
    pipeline = ResearchPipeline(provider, config, RESEARCH_DIR)
    result = pipeline.run(sheet, bundle)
    entry = DecisionLog(DECISION_LOG_DIR).append(result)

    print(result.memo_markdown)
    print(f"Memo: {Path(result.artifact_dir) / 'memo.md'}")
    print(f"Decision log entry: {entry.entry_id}")
    print(f"Verified evidence: {len(result.evidence.verified)}; failed quote check: {len(result.evidence.unverified)}")
    print(f"Figures not traceable to the fact sheet: {len(result.number_findings)}")
    for note in result.notes:
        print(f"Note: {note}")
    print(
        "Record what you did with it:\n"
        f"  python experiments/exp0b/run.py --action {entry.entry_id} watched \"reason\""
    )
    return 0


def record_action(entry_id: str, action: str, reason: str, notes: str | None) -> int:
    record = DecisionLog(DECISION_LOG_DIR).record_user_action(entry_id, action, reason, notes)  # type: ignore[arg-type]
    print(f"Recorded {record.user_action} for {entry_id} at {record.recorded_at.isoformat()}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Experiment 0b: first research memo")
    parser.add_argument("company", nargs="?", default=None, help="Company name or ticker, e.g. NVIDIA or NVDA")
    parser.add_argument("--company", dest="company_flag", default=None, help=argparse.SUPPRESS)
    parser.add_argument(
        "--action",
        nargs=3,
        metavar=("ENTRY_ID", "ACTION", "REASON"),
        help="Record bought | skipped | watched for a decision log entry instead of writing a memo",
    )
    parser.add_argument("--notes", default=None, help="Override notes to store with --action")
    args = parser.parse_args()
    if args.action:
        entry_id, action, reason = args.action
        sys.exit(record_action(entry_id, action, reason, args.notes))
    query = args.company or args.company_flag
    if not query:
        parser.error("give a company name or ticker, e.g. python experiments/exp0b/run.py NVIDIA")
    sys.exit(run_memo(query))


if __name__ == "__main__":
    main()
