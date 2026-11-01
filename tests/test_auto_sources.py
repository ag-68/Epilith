import json
from pathlib import Path

import pytest

from data.config import company_by_ticker
from data.providers.sec_edgar import SecEdgarProvider
from data.snapshots import SnapshotStore
from research.auto_sources import SourcesUnavailable, build_source_bundle
from research.filing_sections import TEN_K_SECTIONS, TEN_Q_SECTIONS, cut_section

ROOT = Path(__file__).resolve().parents[1]
CIK = "1045810"

TEN_K_HTML = """
<html><body>
<table>
<tr><td>Item 1.</td><td>Business</td><td>4</td></tr>
<tr><td>Item 1A.</td><td>Risk Factors</td><td>12</td></tr>
<tr><td>Item 7.</td><td>Management's Discussion and Analysis of Financial Condition and Results of Operations</td><td>30</td></tr>
<tr><td>Item 8.</td><td>Financial Statements</td><td>50</td></tr>
</table>
<p>Item 1. Business</p>
<p>Our Company</p>
<p>NVIDIA pioneered accelerated computing to help solve the most challenging computational problems.</p>
<p>Data Center is our largest market platform and is driven by demand for AI infrastructure.</p>
<p>See Item 1A. Risk Factors in this report for more on supply constraints.</p>
<p>4</p>
<p>Item 1A. Risk Factors</p>
<p>Our business depends on a limited number of suppliers of advanced packaging capacity.</p>
<p>Export controls may restrict sales of our Data Center products to certain countries.</p>
<p>Item 1B. Unresolved Staff Comments</p>
<p>None.</p>
<p>Item 7. Management's Discussion and Analysis of Financial Condition and Results of Operations</p>
<p>Overview</p>
<p>Revenue for fiscal year 2026 was up strongly on Data Center growth.</p>
<p>Item 7A. Quantitative and Qualitative Disclosures About Market Risk</p>
<p>Interest rate risk is limited.</p>
<p>Item 8. Financial Statements and Supplementary Data</p>
<p>Tables follow.</p>
</body></html>
"""

TEN_Q_HTML = """
<html><body>
<p>Part I. Financial Information</p>
<p>Item 1. Financial Statements</p>
<p>Condensed statements follow.</p>
<p>Item 2. Management's Discussion and Analysis of Financial Condition and Results of Operations</p>
<p>Demand for Blackwell exceeded supply during the quarter.</p>
<p>Item 3. Quantitative and Qualitative Disclosures About Market Risk</p>
<p>No material change.</p>
<p>Part II. Other Information</p>
<p>Item 1. Legal Proceedings</p>
<p>Refer to the notes.</p>
<p>Item 1A. Risk Factors</p>
<p>There have been no material changes from the risk factors in our annual report, except export rules tightened.</p>
<p>Item 2. Unregistered Sales of Equity Securities</p>
<p>Repurchases in the table below.</p>
</body></html>
"""

RELEASE_HTML = """
<html><body>
<p>NVIDIA Announces Financial Results for Second Quarter Fiscal 2027</p>
<p>"Blackwell demand is extraordinary," said Jensen Huang.</p>
<p>Outlook: revenue is expected to be $54.0 billion, plus or minus 2%.</p>
</body></html>
"""

SUBMISSIONS = {
    "filings": {
        "recent": {
            "form": ["8-K", "10-Q", "8-K", "10-K", "10-Q"],
            "filingDate": ["2026-08-27", "2026-08-27", "2026-06-01", "2026-02-26", "2025-11-19"],
            "reportDate": ["2026-08-27", "2026-07-26", "2026-05-30", "2026-01-25", "2025-10-26"],
            "accessionNumber": ["0001045810-26-000200", "0001045810-26-000190", "0001045810-26-000150", "0001045810-26-000030", "0001045810-25-000300"],
            "primaryDocument": ["nvda-8k.htm", "nvda-10q.htm", "nvda-8k-other.htm", "nvda-10k.htm", "nvda-10q-old.htm"],
            "items": ["2.02,9.01", "", "5.02", "", ""],
        }
    }
}
INDEX = {"directory": {"item": [{"name": "nvda-8k.htm"}, {"name": "ex991q2fy27.htm"}, {"name": "R1.htm"}]}}


class FakeSec(SecEdgarProvider):
    def __init__(self) -> None:
        super().__init__(user_agent="Test test@example.com")
        self.calls: list[str] = []

    def _get(self, url: str) -> bytes:
        self.calls.append(url)
        if url.endswith(f"CIK000{CIK}.json"):
            return json.dumps(SUBMISSIONS).encode()
        if url.endswith("-index.json"):
            return json.dumps(INDEX).encode()
        if url.endswith("nvda-10k.htm"):
            return TEN_K_HTML.encode()
        if url.endswith("nvda-10q.htm"):
            return TEN_Q_HTML.encode()
        if url.endswith("ex991q2fy27.htm"):
            return RELEASE_HTML.encode()
        raise AssertionError(f"unexpected url {url}")


@pytest.fixture
def company():
    return company_by_ticker("NVDA", ROOT / "config" / "companies.yaml")


def test_cut_section_skips_table_of_contents_and_stops_at_next_item():
    from data.earnings_release import html_to_text

    text = html_to_text(TEN_K_HTML)
    business = cut_section(text, TEN_K_SECTIONS[0])
    assert business is not None
    assert business.text.startswith("Item 1. Business")
    assert "pioneered accelerated computing" in business.text
    assert "limited number of suppliers" not in business.text
    assert "See Item 1A. Risk Factors in this report" in business.text

    risks = cut_section(text, TEN_K_SECTIONS[1])
    assert risks is not None
    assert "Export controls" in risks.text
    assert "Unresolved Staff Comments" not in risks.text

    mdna = cut_section(text, TEN_K_SECTIONS[2])
    assert mdna is not None
    assert "Data Center growth" in mdna.text
    assert "Interest rate risk" not in mdna.text


def test_cut_section_reads_quarterly_parts():
    from data.earnings_release import html_to_text

    text = html_to_text(TEN_Q_HTML)
    mdna = cut_section(text, TEN_Q_SECTIONS[0])
    assert mdna is not None and "Blackwell exceeded supply" in mdna.text
    assert "No material change" not in mdna.text
    risks = cut_section(text, TEN_Q_SECTIONS[1])
    assert risks is not None and "export rules tightened" in risks.text
    assert "Repurchases" not in risks.text


def test_build_source_bundle_writes_manifest_and_reuses_stored_files(tmp_path: Path, company):
    store = SnapshotStore(tmp_path / "data")
    sec = FakeSec()
    bundle, folder = build_source_bundle(company, store, tmp_path / "sources", sec=sec)

    titles = [excerpt.title for excerpt in bundle.excerpts]
    assert len(bundle.excerpts) == 6
    assert any("Form 10-K" in t and "Item 1. Business" in t for t in titles)
    assert any("Form 10-Q, period ended 26 July 2026" in t and "Item 2." in t for t in titles)
    assert any("earnings release filed 27 August 2026" in t for t in titles)
    kinds = {excerpt.kind for excerpt in bundle.excerpts}
    assert kinds == {"filing", "ir_release"}
    assert all(excerpt.url and "sec.gov/Archives" in excerpt.url for excerpt in bundle.excerpts)
    assert len({excerpt.source_id for excerpt in bundle.excerpts}) == 6

    manifest = (folder / "sources.yaml").read_text(encoding="utf-8")
    assert "rules_version" in manifest and "raw_hash" in manifest
    raw_files = list((tmp_path / "data" / "raw" / "sec_edgar" / "NVDA").glob("*.htm"))
    assert len(raw_files) == 3

    # Same filings again: nothing downloaded except the small filing list, same folder, no rewrite.
    fetched_before = len(sec.calls)
    again, folder_again = build_source_bundle(company, store, tmp_path / "sources", sec=sec)
    assert folder_again == folder
    assert again.bundle_id == bundle.bundle_id
    assert [url for url in sec.calls[fetched_before:] if not url.endswith(f"CIK000{CIK}.json")] == []


def test_build_source_bundle_refuses_non_us_filers(tmp_path: Path):
    asml = company_by_ticker("ASML", ROOT / "config" / "companies.yaml")
    with pytest.raises(SourcesUnavailable, match="hand|excerpts"):
        build_source_bundle(asml, SnapshotStore(tmp_path / "data"), tmp_path / "sources", sec=FakeSec())
