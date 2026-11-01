from pathlib import Path

from research.facts import latest_report_for, load_fact_sheet
from research.formatting import fact_sheet_text

ROOT = Path(__file__).resolve().parents[1]


def test_latest_report_prefers_full_three_company_runs():
    path, report = latest_report_for("NVDA", ROOT / "experiments" / "exp0a" / "output")
    assert "NVDA_ASML_TSMC" in path.name
    assert report.overall_passed


def test_fact_sheet_from_committed_0a_output():
    sheet = load_fact_sheet("NVDA")
    metrics = {line.metric for line in sheet.facts}
    assert {"revenue", "net_income", "operating_cash_flow", "capex", "total_debt", "cash", "price"} <= metrics
    assert {line.metric for line in sheet.excluded} == {"shares_outstanding"}
    assert sheet.currency == "USD"
    text = fact_sheet_text(sheet)
    assert "Revenue: USD 302.97 billion" in text
    assert "Trailing P/E: 25.6x" in text
    assert "Not validated in 0a" in text
