from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from data.models import ClaimType, FinancialFact, PeriodType


def test_computed_fact_requires_formula():
    with pytest.raises(ValidationError):
        FinancialFact(
            fact_id="x",
            metric="revenue",
            value=Decimal("1"),
            unit="USD",
            currency="USD",
            period_type=PeriodType.ttm,
            period_start_date=date(2025, 1, 1),
            period_end_date=date(2025, 12, 31),
            definition="x",
            source_id="s",
            retrieved_at=datetime.now(timezone.utc),
            content_hash="h",
            claim_type=ClaimType.computed,
        )


def test_listing_is_not_mixed_into_currency_field():
    fact = FinancialFact(
        fact_id="x",
        metric="cash",
        value=Decimal("1"),
        unit="TWD",
        currency="TWD",
        period_type=PeriodType.point_in_time,
        as_of_date=date(2026, 1, 1),
        listing="TWSE:2330",
        definition="cash",
        source_id="s",
        retrieved_at=datetime.now(timezone.utc),
        content_hash="h",
        claim_type=ClaimType.reported,
    )
    assert fact.currency == "TWD"
    assert fact.listing == "TWSE:2330"
    assert fact.listing != fact.currency
