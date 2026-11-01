from datetime import date, datetime, timezone
from decimal import Decimal

from data.models import (
    ClaimType,
    Company,
    Confirmation,
    CrossCheck,
    DiscrepancyClass,
    FieldStatus,
    FinancialFact,
    FinancialSnapshot,
    MarketFact,
    PeriodType,
    Source,
    ValuationPanel,
)
from validation.data_quality import evaluate_company

NOW = datetime(2026, 10, 31, tzinfo=timezone.utc)


def _company() -> Company:
    return Company(
        ticker="MU",
        name="Micron Technology Inc.",
        cik="0000723125",
        region="US",
        accounting="US GAAP",
        reporting_currency="USD",
        listing="NASDAQ:MU",
        exchange="NASDAQ",
        valuation_currency="USD",
        yahoo_symbol="MU",
        stooq_symbol="mu.us",
    )


def _source(source_id: str, origin: str) -> Source:
    return Source(source_id=source_id, origin=origin, name=origin, retrieved_at=NOW, content_hash="h" * 64)


def _flow(metric: str, value: str, source_id: str) -> FinancialFact:
    return FinancialFact(
        fact_id=f"{metric}-ttm",
        metric=metric,
        value=Decimal(value),
        unit="USD",
        currency="USD",
        period_type=PeriodType.ttm,
        period_start_date=date(2025, 8, 29),
        period_end_date=date(2026, 9, 3),
        definition="d",
        source_id=source_id,
        retrieved_at=NOW,
        content_hash="c" * 64,
        claim_type=ClaimType.computed,
        formula="sum(latest_4_reported_quarters)",
    )


def _instant(metric: str, value: str, source_id: str, unit: str = "USD") -> FinancialFact:
    return FinancialFact(
        fact_id=f"{metric}-pit",
        metric=metric,
        value=Decimal(value),
        unit=unit,
        currency=None if unit != "USD" else "USD",
        period_type=PeriodType.point_in_time,
        as_of_date=date(2026, 9, 3),
        definition="d",
        source_id=source_id,
        retrieved_at=NOW,
        content_hash="c" * 64,
        claim_type=ClaimType.reported,
    )


def _snapshot() -> FinancialSnapshot:
    return FinancialSnapshot(
        snapshot_id="s",
        company=_company(),
        facts=[
            _flow("revenue", "133188000000", "filing"),
            _flow("operating_income", "99340000000", "filing"),
            _flow("net_income", "84969000000", "filing"),
            _flow("operating_cash_flow", "89675000000", "filing"),
            _flow("capex", "30712000000", "release"),
            _instant("total_debt", "2792000000", "filing"),
            _instant("cash", "38364000000", "filing"),
            _instant("shares_outstanding", "1131423212", "filing", unit="shares"),
            _instant("reporting_currency", "1", "filing", unit="USD"),
            _instant("fiscal_period", str(date(2026, 9, 3).toordinal()), "filing", unit="date_ordinal"),
            _instant("listing", "1", "filing", unit="NASDAQ:MU"),
        ],
        market=MarketFact(
            fact_id="p",
            price=Decimal("884.74"),
            currency="USD",
            listing="NASDAQ:MU",
            as_of_timestamp=NOW,
            market_status="eod",
            source_id="quote",
            retrieved_at=NOW,
            content_hash="m" * 64,
        ),
        sources=[_source("filing", "sec_edgar"), _source("release", "company_report"), _source("quote", "stooq")],
        created_at=NOW,
    )


def _check(metric: str, primary: str, other: str, passed: bool, classification=None, explanation=None) -> CrossCheck:
    return CrossCheck(
        metric=metric,
        primary_value=Decimal(primary),
        primary_source_id="filing",
        cross_check_value=Decimal(other),
        cross_check_source_id="release",
        passed=passed,
        classification=classification,
        explanation=explanation,
    )


def test_regulator_figure_counts_without_a_second_document():
    result = evaluate_company(_snapshot(), ValuationPanel(listing="NASDAQ:MU", currency="USD"), [])
    assert result.valid_count == 12
    assert result.confirmed_count == 0
    revenue = next(f for f in result.fields if f.metric == "revenue")
    assert revenue.status is FieldStatus.valid
    assert revenue.confirmation is Confirmation.unconfirmed
    assert revenue.provenance == "authority"
    assert "No second document states this line" in revenue.notes
    assert result.passed


def test_second_document_confirms_explains_or_disputes_but_never_fails():
    checks = [
        _check("revenue", "133188000000", "133190000000", passed=True),
        _check(
            "net_income",
            "84969000000",
            "80000000000",
            passed=False,
            classification=DiscrepancyClass.accounting_definition,
            explanation="Same year, different accounting rules.",
        ),
        _check("cash", "38364000000", "30000000000", passed=False, classification=DiscrepancyClass.unresolved),
    ]
    result = evaluate_company(_snapshot(), ValuationPanel(listing="NASDAQ:MU", currency="USD"), checks)
    by_metric = {f.metric: f for f in result.fields}
    assert by_metric["revenue"].confirmation is Confirmation.confirmed
    assert by_metric["net_income"].confirmation is Confirmation.explained
    assert by_metric["cash"].confirmation is Confirmation.disputed
    assert all(by_metric[m].status is FieldStatus.valid for m in ("revenue", "net_income", "cash"))
    assert result.valid_count == 12 and result.confirmed_count == 1
    assert any("disagrees on cash" in note for note in result.findings)
    assert len(result.discrepancies) == 3


def test_company_only_lines_are_named_in_findings():
    result = evaluate_company(_snapshot(), ValuationPanel(listing="NASDAQ:MU", currency="USD"), [])
    capex = next(f for f in result.fields if f.metric == "capex")
    assert capex.provenance == "company"
    assert any("capex come from the company's own release only" in note for note in result.findings)
