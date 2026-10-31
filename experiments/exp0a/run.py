from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")

from data.config import DATA_DIR, company_by_ticker  # noqa: E402
from data.ingestion import CompanyIngestor  # noqa: E402
from data.models import ExperimentReport  # noqa: E402
from validation.data_quality import evaluate_company  # noqa: E402
from valuation.multiples import compute_panel  # noqa: E402


OUTPUT_DIR = ROOT / "experiments" / "exp0a" / "output"


def render_markdown(report: ExperimentReport) -> str:
    lines = [
        "# Experiment 0a report",
        "",
        f"Generated at: {report.generated_at.isoformat()}",
        f"Overall: {'PASS' if report.overall_passed else 'FAIL'}",
        "",
    ]
    for company in report.companies:
        lines.append(f"## {company.ticker}: {company.valid_count}/12 valid")
        lines.append("")
        lines.append(
            "| Metric | Value | Unit | Currency | Period/As-of | Source | Cross-check source | Cross-check value | Difference | Status |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for field in company.fields:
            lines.append(
                "| {metric} | {value} | {unit} | {currency} | {period} | {source} | {xsrc} | {xval} | {diff} | {status} |".format(
                    metric=field.metric,
                    value=field.value,
                    unit=field.unit,
                    currency=field.currency,
                    period=field.period_label,
                    source=(field.source_id or "")[:12],
                    xsrc=(field.cross_check_source_id or "")[:12],
                    xval=field.cross_check_value,
                    diff=field.difference,
                    status=field.status.value,
                )
            )
        lines.append("")
        if company.valuation:
            val = company.valuation
            lines.append("### Valuation panel")
            lines.append("")
            lines.append(f"- Listing: {val.listing} ({val.currency})")
            lines.append(f"- Price: {val.price} as of {val.price_as_of}")
            lines.append(f"- Shares: {val.shares_outstanding}")
            lines.append(f"- Market cap: {val.market_cap}")
            lines.append(f"- Total debt: {val.total_debt}")
            lines.append(f"- Cash: {val.cash}")
            lines.append(f"- EV: {val.enterprise_value}")
            lines.append(f"- TTM revenue: {val.ttm_revenue} (end {val.ttm_end_date})")
            lines.append(f"- TTM net income: {val.ttm_net_income}")
            lines.append(f"- TTM FCF: {val.fcf}")
            lines.append(f"- Trailing P/E: {val.trailing_pe}")
            lines.append(f"- EV/Sales: {val.ev_sales}")
            lines.append(f"- FCF yield: {val.fcf_yield}")
            lines.append(f"- Balance sheet as of: {val.balance_sheet_as_of}")
            for note in val.notes:
                lines.append(f"- Note: {note}")
            lines.append("")
        if company.discrepancies:
            lines.append("### Discrepancies")
            lines.append("")
            for item in company.discrepancies:
                lines.append(
                    f"- {item.metric}: passed={item.passed} class={item.classification} "
                    f"primary={item.primary_value} cross={item.cross_check_value} pct={item.difference_pct} "
                    f"{item.explanation or ''}"
                )
            lines.append("")
        if company.findings:
            lines.append("### Findings")
            lines.append("")
            for finding in company.findings:
                lines.append(f"- {finding}")
            lines.append("")
    if report.findings:
        lines.append("## Experiment findings")
        lines.append("")
        for finding in report.findings:
            lines.append(f"- {finding}")
        lines.append("")
    return "\n".join(lines)


def run(tickers: list[str]) -> ExperimentReport:
    ingestor = CompanyIngestor()
    companies = []
    findings = [
        "Experiment 0a only. No agents, no LLM calls, no portfolio, no screening.",
        f"Raw artifacts stored under {DATA_DIR / 'raw'}.",
    ]
    for ticker in tickers:
        company_by_ticker(ticker)
        snapshot, checks = ingestor.ingest(ticker)
        panel = compute_panel(snapshot)
        companies.append(evaluate_company(snapshot, panel, checks))
    overall = all(item.passed for item in companies) and len(companies) == 3
    if len(tickers) < 3:
        findings.append(
            "Full 0a pass requires NVDA, ASML and TSMC. This run is a subset and cannot pass the experiment."
        )
        overall = False
    return ExperimentReport(
        generated_at=datetime.now(timezone.utc),
        companies=companies,
        overall_passed=overall,
        findings=findings,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Experiment 0a data validation")
    parser.add_argument("--company", action="append", dest="companies", help="Ticker to run (repeatable)")
    args = parser.parse_args()
    tickers = [t.upper() for t in (args.companies or ["NVDA", "ASML", "TSMC"])]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report = run(tickers)
    stamp = report.generated_at.strftime("%Y%m%dT%H%M%SZ")
    json_path = OUTPUT_DIR / f"report_{'_'.join(tickers)}_{stamp}.json"
    md_path = OUTPUT_DIR / f"report_{'_'.join(tickers)}_{stamp}.md"
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(render_markdown(report))
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    if any(not company.passed for company in report.companies):
        sys.exit(1)


if __name__ == "__main__":
    main()
