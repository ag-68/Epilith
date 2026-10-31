from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal


QUARTER_MIN_DAYS = 80
QUARTER_MAX_DAYS = 105
ANNUAL_MIN_DAYS = 350
ANNUAL_MAX_DAYS = 380
YTD_MIN_DAYS = 160
YTD_MAX_DAYS = 290


def days_between(start: date, end: date) -> int:
    return (end - start).days


def classify_duration(start: date, end: date) -> str:
    days = days_between(start, end)
    if QUARTER_MIN_DAYS <= days <= QUARTER_MAX_DAYS:
        return "quarterly"
    if ANNUAL_MIN_DAYS <= days <= ANNUAL_MAX_DAYS:
        return "annual"
    if YTD_MIN_DAYS <= days <= YTD_MAX_DAYS:
        return "ytd"
    return "other"


@dataclass(frozen=True)
class DurationAmount:
    start: date
    end: date
    value: Decimal
    accession: str | None = None
    filed: date | None = None
    concept: str | None = None


@dataclass(frozen=True)
class QuarterAmount:
    start: date
    end: date
    value: Decimal
    derived: bool
    formula: str | None = None
    input_keys: tuple[tuple[date, date], ...] = ()
    accession: str | None = None
    concept: str | None = None


def _key(item: DurationAmount) -> tuple[date, date]:
    return (item.start, item.end)


def fill_quarters(
    quarterly: list[DurationAmount],
    ytd: list[DurationAmount],
    annual: list[DurationAmount],
) -> list[QuarterAmount]:
    """Build a standalone-quarter series, deriving missing quarters from YTD/annual."""
    reported = {item.end: QuarterAmount(
        start=item.start,
        end=item.end,
        value=item.value,
        derived=False,
        accession=item.accession,
        concept=item.concept,
    ) for item in sorted(quarterly, key=lambda i: i.end)}

    by_start: dict[date, list[DurationAmount]] = {}
    for item in [*ytd, *annual, *quarterly]:
        by_start.setdefault(item.start, []).append(item)

    derived: list[QuarterAmount] = []
    for fiscal_start, items in by_start.items():
        unique: dict[tuple[date, date], DurationAmount] = {}
        for item in items:
            unique[_key(item)] = item
        ordered = sorted(unique.values(), key=lambda i: i.end)
        classified = [(classify_duration(i.start, i.end), i) for i in ordered]
        q1 = next((i for kind, i in classified if kind == "quarterly" and i.start == fiscal_start), None)
        h1 = next((i for kind, i in classified if kind == "ytd" and QUARTER_MAX_DAYS < days_between(i.start, i.end) <= 200), None)
        nine_mo = next((i for kind, i in classified if kind == "ytd" and days_between(i.start, i.end) > 200), None)
        fy = next((i for kind, i in classified if kind == "annual"), None)

        if q1 and q1.end not in reported:
            reported[q1.end] = QuarterAmount(q1.start, q1.end, q1.value, False, accession=q1.accession, concept=q1.concept)

        if h1 and q1 and h1.end not in reported:
            derived.append(
                QuarterAmount(
                    start=q1.end + timedelta(days=1),
                    end=h1.end,
                    value=h1.value - q1.value,
                    derived=True,
                    formula="ytd_h1 - q1",
                    input_keys=(_key(q1), _key(h1)),
                    accession=h1.accession,
                    concept=h1.concept,
                )
            )
        if nine_mo and h1 and nine_mo.end not in reported:
            derived.append(
                QuarterAmount(
                    start=h1.end + timedelta(days=1),
                    end=nine_mo.end,
                    value=nine_mo.value - h1.value,
                    derived=True,
                    formula="ytd_9m - ytd_h1",
                    input_keys=(_key(h1), _key(nine_mo)),
                    accession=nine_mo.accession,
                    concept=nine_mo.concept,
                )
            )
        if fy:
            prior = nine_mo or h1 or q1
            if prior and fy.end not in reported:
                derived.append(
                    QuarterAmount(
                        start=prior.end + timedelta(days=1),
                        end=fy.end,
                        value=fy.value - prior.value,
                        derived=True,
                        formula="annual - prior_ytd",
                        input_keys=(_key(prior), _key(fy)),
                        accession=fy.accession,
                        concept=fy.concept,
                    )
                )

    by_end = dict(reported)
    for item in derived:
        by_end.setdefault(item.end, item)

    for fiscal_start, items in by_start.items():
        fy = next((i for i in items if classify_duration(i.start, i.end) == "annual"), None)
        if fy is None or fy.end in by_end:
            continue
        in_year = [
            q for q in by_end.values()
            if q.end <= fy.end and q.start >= fiscal_start
        ]
        if len(in_year) == 3:
            total = sum((q.value for q in in_year), Decimal("0"))
            last_end = max(q.end for q in in_year)
            by_end[fy.end] = QuarterAmount(
                start=last_end + timedelta(days=1),
                end=fy.end,
                value=fy.value - total,
                derived=True,
                formula="annual - (q1+q2+q3)",
                input_keys=tuple((q.start, q.end) for q in sorted(in_year, key=lambda i: i.end)),
                accession=fy.accession,
                concept=fy.concept,
            )
    return sorted(by_end.values(), key=lambda i: i.end)


def last_n_quarters(quarters: list[QuarterAmount], n: int = 4) -> list[QuarterAmount]:
    if len(quarters) < n:
        return quarters
    return quarters[-n:]
