from decimal import Decimal

from data.earnings_release import extract_metrics


def test_does_not_treat_a_year_as_revenue():
    html = "<p>Revenue for 2026 of $96.2 billion.</p>"
    found = extract_metrics(html)
    assert found["revenue"]["value"] == Decimal("96200000000")


def test_extracts_headline_revenue_in_billions():
    html = """
    <html><body>
    <p>NVIDIA today reported revenue for the second quarter of $96.2 billion,
    compared with $46.7 billion a year earlier.</p>
    <p>GAAP net income was $59.7 billion.</p>
    <p>Operating income was $63.7 billion.</p>
    </body></html>
    """
    found = extract_metrics(html)
    assert found["revenue"]["value"] == Decimal("96200000000")
    assert found["net_income"]["value"] == Decimal("59700000000")
    assert found["operating_income"]["value"] == Decimal("63700000000")


def test_extracts_millions_table_with_newlines():
    html = """
    <p>(In millions)</p>
    <table>
      <tr><td>Net income</td><td>$</td><td>59,688</td></tr>
      <tr><td>Net cash provided by operating activities</td><td>24,077</td></tr>
      <tr><td>Cash and cash equivalents</td><td>$</td><td>22,443</td></tr>
      <tr><td>Short-term debt</td><td>1,000</td></tr>
      <tr><td>Long-term debt</td><td>32,366</td></tr>
      <tr><td>Purchases related to property and equipment and intangible assets</td><td>(2,677)</td></tr>
    </table>
    """
    found = extract_metrics(html)
    assert found["net_income"]["value"] == Decimal("59688000000")
    assert found["operating_cash_flow"]["value"] == Decimal("24077000000")
    assert found["cash"]["value"] == Decimal("22443000000")
    assert found["total_debt"]["value"] == Decimal("33366000000")
    assert found["capex"]["value"] == Decimal("2677000000")
