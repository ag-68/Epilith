from datetime import date, datetime, timezone
from decimal import Decimal

from data.models import (
    ClaimType,
    Company,
    FinancialFact,
    FinancialSnapshot,
    MarketFact,
    PeriodType,
)
from valuation.multiples import compute_panel


def _company() -> Company:
    return Company(
        ticker="NVDA",
        name="NVIDIA Corporation",
        cik="0001045810",
        region="US",
        accounting="US GAAP",
        reporting_currency="USD",
        listing="NASDAQ:NVDA",
        exchange="NASDAQ",
        valuation_currency="USD",
        yahoo_symbol="NVDA",
        stooq_symbol="nvda.us",
    )


def _fact(metric: str, value: str, period_type: PeriodType, **kwargs) -> FinancialFact:
    defaults = {
        "fact_id": metric + period_type.value,
        "unit": "USD",
        "currency": "USD",
        "listing": "NASDAQ:NVDA",
        "definition": "test",
        "source_id": "src",
        "retrieved_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "content_hash": "abc",
        "claim_type": ClaimType.computed if period_type is PeriodType.ttm else ClaimType.reported,
        "formula": "sum(q)" if period_type is PeriodType.ttm else None,
    }
    defaults.update(kwargs)
    if period_type is PeriodType.ttm:
        defaults.setdefault("period_start_date", date(2025, 7, 28))
        defaults.setdefault("period_end_date", date(2026, 7, 26))
    if period_type is PeriodType.point_in_time:
        defaults.setdefault("as_of_date", date(2026, 7, 26))
    return FinancialFact(metric=metric, value=Decimal(value), period_type=period_type, **defaults)


def test_valuation_formulas():
    snapshot = FinancialSnapshot(
        snapshot_id="s",
        company=_company(),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        facts=[
            _fact("revenue", "100", PeriodType.ttm),
            _fact("net_income", "20", PeriodType.ttm),
            _fact("operating_cash_flow", "30", PeriodType.ttm),
            _fact("capex", "5", PeriodType.ttm),
            _fact("total_debt", "10", PeriodType.point_in_time),
            _fact("cash", "4", PeriodType.point_in_time),
            _fact("shares_outstanding", "2", PeriodType.point_in_time, unit="shares", currency=None),
        ],
        market=MarketFact(
            fact_id="px",
            price=Decimal("10"),
            currency="USD",
            listing="NASDAQ:NVDA",
            as_of_timestamp=datetime(2026, 7, 26, tzinfo=timezone.utc),
            market_status="closed",
            source_id="mkt",
            retrieved_at=datetime(2026, 7, 26, tzinfo=timezone.utc),
            content_hash="p",
        ),
    )
    panel = compute_panel(snapshot)
    assert panel.market_cap == Decimal("20")
    assert panel.enterprise_value == Decimal("26")
    assert panel.trailing_pe == Decimal("1")
    assert panel.ev_sales == Decimal("0.26")
    assert panel.fcf == Decimal("25")
    assert panel.fcf_yield == Decimal("1.25")
