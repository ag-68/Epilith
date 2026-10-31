from datetime import date
from decimal import Decimal

from data.periods import DurationAmount, fill_quarters, last_n_quarters


def _amt(start: str, end: str, value: int) -> DurationAmount:
    return DurationAmount(date.fromisoformat(start), date.fromisoformat(end), Decimal(value))


def test_ytd_and_annual_expand_to_four_quarters():
    quarterly = [
        _amt("2025-01-27", "2025-04-27", 44),  # Q1
        _amt("2025-04-28", "2025-07-27", 47),  # Q2 reported
        _amt("2025-07-28", "2025-10-26", 57),  # Q3 reported
    ]
    ytd = [
        _amt("2025-01-27", "2025-07-27", 91),
        _amt("2025-01-27", "2025-10-26", 148),
    ]
    annual = [_amt("2025-01-27", "2026-01-25", 216)]
    quarters = fill_quarters(quarterly, ytd, annual)
    last4 = last_n_quarters(quarters, 4)
    assert [q.end.isoformat() for q in last4] == [
        "2025-04-27",
        "2025-07-27",
        "2025-10-26",
        "2026-01-25",
    ]
    q4 = last4[-1]
    assert q4.derived is True
    assert q4.value == Decimal("68")


def test_cash_flow_ytd_only_derives_q2():
    quarterly = [_amt("2026-01-26", "2026-04-26", 50)]
    ytd = [_amt("2026-01-26", "2026-07-26", 74)]
    quarters = fill_quarters(quarterly, ytd, [])
    assert len(quarters) == 2
    assert quarters[0].value == Decimal("50")
    assert quarters[1].derived is True
    assert quarters[1].value == Decimal("24")
    assert quarters[1].start == date(2026, 4, 27)
