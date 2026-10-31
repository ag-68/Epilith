from __future__ import annotations

import io
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
from pypdf import PdfReader

from data.earnings_release import extract_metrics, html_to_text
from data.html_tables import html_tables_to_text
from data.http import browser_headers
from data.http import client as http_client
from data.models import Company, Source
from data.snapshots import SnapshotStore
from data.statement_table import StatedAmount, parse_statement_text


@dataclass
class CompanyReport:
    amounts: list[StatedAmount] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    headlines: dict[str, dict[str, Any]] = field(default_factory=dict)
    headline_source_id: str | None = None
    statement_language: str = ""


class CompanyReportProvider:
    """Company quarterly report. This is a different document from the home-market feed."""

    origin = "company_report"

    def __init__(self, timeout: float = 60.0) -> None:
        self.timeout = timeout

    def fetch(self, company: Company, store: SnapshotStore) -> CompanyReport:
        report = CompanyReport()
        if not company.ir_release_urls:
            report.notes.append("No company quarterly-report address is configured.")
            return report
        try:
            with http_client(browser_headers(), self.timeout) as http:
                pages = self._collect_pages(http, company.ir_release_urls[0])
                for page_url, html in pages:
                    source = store.save_raw(
                        origin=self.origin,
                        ticker=company.ticker,
                        filename="quarterly_page.html",
                        content=html,
                        url=page_url,
                        name="Company quarterly results page",
                    )
                    report.sources.append(source)
                    page_html = html.decode("utf-8", errors="replace")
                    if "us gaap" in page_html.lower():
                        report.statement_language = "US GAAP"
                    pdf_urls = _statement_pdfs(page_html, page_url)
                    if not pdf_urls:
                        table_text = html_tables_to_text(page_html)
                        parsed_amounts = parse_statement_text(
                            table_text, company.reporting_currency, source.source_id
                        )
                        if not parsed_amounts:
                            parsed_amounts = parse_statement_text(
                                html_to_text(page_html), company.reporting_currency, source.source_id
                            )
                        report.amounts.extend(parsed_amounts)
                        if not report.headlines:
                            parsed = extract_metrics(page_html)
                            if parsed:
                                report.headlines = parsed
                                report.headline_source_id = source.source_id
                        continue
                    for pdf_url in pdf_urls:
                        content = _get(http, pdf_url)
                        pdf_source = store.save_raw(
                            origin=self.origin,
                            ticker=company.ticker,
                            filename="financial_statements.pdf",
                            content=content,
                            url=pdf_url,
                            name="Company quarterly financial statements",
                        )
                        report.sources.append(pdf_source)
                        pdf_text = _pdf_text(content)
                        if "us gaap" in pdf_text.lower():
                            report.statement_language = "US GAAP"
                        report.amounts.extend(
                            parse_statement_text(
                                pdf_text,
                                company.reporting_currency,
                                pdf_source.source_id,
                            )
                        )
        except (httpx.HTTPError, OSError) as exc:
            saved = self._saved_copy(company, store, str(exc))
            if saved.sources:
                _label_statement(saved, company)
                return saved
            report.notes.append(f"Company report download failed and no stored copy exists. {exc}")
            return report
        if not report.amounts and not report.headlines:
            report.notes.append("The company report was downloaded, but no quarterly table was read from it.")
        else:
            report.notes.append("Company quarterly report was downloaded and read as the separate document.")
        _label_statement(report, company)
        return report

    def _collect_pages(self, http: httpx.Client, start_url: str) -> list[tuple[str, bytes]]:
        first = _get(http, start_url)
        pages = [(start_url, first)]
        html = first.decode("utf-8", errors="replace")
        for url in _quarter_pages(html, start_url):
            try:
                pages.append((url, _get(http, url)))
            except httpx.HTTPError:
                continue
        added = 0
        for url in _earlier_fiscal_releases(start_url):
            if added >= 3:
                break
            try:
                body = _get(http, url)
            except httpx.HTTPError:
                continue
            lowered = body.lower()
            if b"announces financial results" not in lowered or b"three months" not in lowered:
                continue
            pages.append((url, body))
            added += 1
        return pages

    def _saved_copy(self, company: Company, store: SnapshotStore, error: str) -> CompanyReport:
        report = CompanyReport()
        cached = store.latest_raw(self.origin, company.ticker, "statement.txt")
        if cached is None or not cached.raw_path:
            return report
        text = Path(cached.raw_path).read_text(encoding="utf-8", errors="replace")
        if "us gaap" in text.lower():
            report.statement_language = "US GAAP"
        cached = cached.model_copy(
            update={
                "metadata": {
                    **cached.metadata,
                    "used_saved_copy": True,
                    "live_fetch_error": error,
                }
            }
        )
        report.sources.append(cached)
        report.amounts.extend(parse_statement_text(text, company.reporting_currency, cached.source_id))
        report.notes.append(
            "The company site refused the live download. "
            "Using the stored quarterly statement from an earlier retrieval. "
            f"Live error: {error}"
        )
        _label_statement(report, company)
        return report


def _get(http: httpx.Client, url: str) -> bytes:
    response = http.get(url)
    response.raise_for_status()
    return response.content


def _pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _label_statement(report: CompanyReport, company: Company) -> None:
    """Mark every line with the rules that statement uses."""
    language = report.statement_language or company.accounting
    report.amounts = [replace(item, accounting=language) for item in report.amounts]
    for source in report.sources:
        source.metadata["accounting"] = language


def _statement_pdfs(html: str, page_url: str) -> list[str]:
    chosen: list[str] = []
    for href, label in re.findall(r'<a[^>]+href="([^"]+\.pdf)"[^>]*>(.*?)</a>', html, flags=re.I | re.S):
        text = re.sub(r"<[^>]+>", " ", label)
        text = re.sub(r"\s+", " ", text).strip().lower()
        if "financial statement" in text:
            chosen.append(urljoin(page_url, href))
    return chosen[:1]


_QUARTER_WORDS = ("first", "second", "third", "fourth")


def _earlier_fiscal_releases(url: str) -> list[str]:
    """Previous quarterly-result addresses that follow the same newsroom pattern."""
    match = re.search(
        r"(first|second|third|fourth)-quarter(?:-and)?-fiscal-(\d{4})",
        url,
        re.I,
    )
    if match is None:
        return []
    index = _QUARTER_WORDS.index(match.group(1).lower())
    year = int(match.group(2))
    found: list[str] = []
    for _step in range(3):
        index -= 1
        if index < 0:
            index = 3
            year -= 1
        word = _QUARTER_WORDS[index]
        slugs = [f"{word}-quarter-fiscal-{year}"]
        if word == "fourth":
            slugs.insert(0, f"{word}-quarter-and-fiscal-{year}")
        for slug in slugs:
            candidate = re.sub(
                r"(first|second|third|fourth)-quarter(?:-and)?-fiscal-\d{4}",
                slug,
                url,
                count=1,
                flags=re.I,
            )
            if candidate not in found and candidate.rstrip("/") != url.rstrip("/"):
                found.append(candidate)
    return found


def _quarter_pages(html: str, page_url: str) -> list[str]:
    year_match = re.search(r"/(20\d{2})/q([1-4])", page_url, re.I)
    if year_match is None:
        return []
    minimum_year = int(year_match.group(1)) - 1
    english_only = "/english/" in page_url.lower()
    found: list[str] = []
    for href in re.findall(r'href="([^"]+)"', html, flags=re.I):
        absolute = urljoin(page_url, href).split("?")[0].rstrip("/")
        match = re.search(r"/(20\d{2})/q([1-4])$", absolute, re.I)
        if match is None:
            continue
        if english_only and "/english/" not in absolute.lower():
            continue
        if int(match.group(1)) < minimum_year:
            continue
        if absolute == page_url.rstrip("/"):
            continue
        found.append(absolute)
    unique = sorted(set(found), key=_quarter_key, reverse=True)
    return unique[:5]


def _quarter_key(url: str) -> tuple[int, int]:
    match = re.search(r"/(20\d{2})/q([1-4])", url, re.I)
    if match is None:
        return (0, 0)
    return int(match.group(1)), int(match.group(2))
