from __future__ import annotations

from decimal import Decimal

from data.models import (
    CompanyValidation,
    CrossCheck,
    DiscrepancyClass,
    FieldResult,
    FieldStatus,
    FinancialFact,
    FinancialSnapshot,
    MarketFact,
    PeriodType,
    ValuationPanel,
)


REQUIRED_FIELDS = [
    "revenue",
    "operating_income",
    "net_income",
    "operating_cash_flow",
    "capex",
    "total_debt",
    "cash",
    "shares_outstanding",
    "price",
    "reporting_currency",
    "fiscal_period",
    "listing",
]

MANDATORY_CROSS_CHECK = {
    "revenue",
    "net_income",
    "operating_cash_flow",
    "capex",
    "total_debt",
    "cash",
    "shares_outstanding",
    "price",
}

TOLERANCE = Decimal("0.01")


def _pct_diff(primary: Decimal, other: Decimal) -> Decimal | None:
    if primary == 0:
        return None
    return abs(primary - other) / abs(primary)


def source_accounting(snapshot: FinancialSnapshot, source_id: str | None) -> str:
    if source_id:
        for source in snapshot.sources:
            if source.source_id == source_id:
                labeled = source.metadata.get("accounting")
                if isinstance(labeled, str) and labeled:
                    return labeled
                break
    return snapshot.company.accounting


def home_flow_fact(snapshot: FinancialSnapshot, metric: str) -> FinancialFact | None:
    """Prefer the home market's own accounting rules when the quarterly statement uses others."""
    ttm = snapshot.latest_fact(metric, PeriodType.ttm)
    annual = snapshot.latest_fact(metric, PeriodType.annual)
    if annual is not None and ttm is not None:
        ttm_rules = source_accounting(snapshot, ttm.source_id)
        annual_rules = source_accounting(snapshot, annual.source_id)
        if ttm_rules != snapshot.company.accounting and annual_rules == snapshot.company.accounting:
            return annual
    return ttm or annual


def _period_label(fact: FinancialFact | None, market: MarketFact | None = None) -> str | None:
    if market is not None:
        return market.as_of_timestamp.isoformat()
    if fact is None:
        return None
    if fact.period_type is PeriodType.ttm:
        return f"TTM {fact.period_start_date} to {fact.period_end_date}"
    if fact.period_type is PeriodType.point_in_time:
        return f"as of {fact.as_of_date}"
    return f"{fact.period_type.value} {fact.period_start_date} to {fact.period_end_date}"


def _fact_valid(fact: FinancialFact | None, market: MarketFact | None = None) -> tuple[bool, list[str]]:
    notes: list[str] = []
    if market is not None:
        missing = []
        if market.price is None:
            missing.append("price")
        if not market.currency:
            missing.append("currency")
        if not market.listing:
            missing.append("listing")
        if not market.as_of_timestamp:
            missing.append("as_of")
        if not market.source_id:
            missing.append("source")
        if missing:
            notes.append("Missing " + ", ".join(missing))
            return False, notes
        return True, notes
    if fact is None:
        return False, ["not obtained"]
    missing = []
    if fact.value is None:
        missing.append("value")
    if not fact.unit:
        missing.append("unit")
    if fact.period_type in {PeriodType.quarterly, PeriodType.annual, PeriodType.ttm}:
        if fact.period_start_date is None or fact.period_end_date is None:
            missing.append("period")
    if fact.period_type is PeriodType.point_in_time and fact.as_of_date is None:
        missing.append("as_of")
    if not fact.source_id:
        missing.append("source")
    if fact.metric not in {"shares_outstanding", "fiscal_period", "listing"} and not fact.currency:
        missing.append("currency")
    if missing:
        notes.append("Missing " + ", ".join(missing))
        return False, notes
    return True, notes


def evaluate_company(
    snapshot: FinancialSnapshot,
    valuation: ValuationPanel,
    cross_checks: list[CrossCheck],
) -> CompanyValidation:
    checks = {c.metric: c for c in cross_checks}
    fields: list[FieldResult] = []
    discrepancies: list[CrossCheck] = []

    for metric in REQUIRED_FIELDS:
        market = snapshot.market if metric == "price" else None
        fact = None if metric == "price" else snapshot.latest_fact(
            metric, PeriodType.ttm if metric in REQUIRED_FIELDS[:5] else None
        )
        if metric in REQUIRED_FIELDS[:5]:
            fact = home_flow_fact(snapshot, metric)
        elif metric == "price":
            fact = None
        else:
            fact = snapshot.latest_fact(metric)

        ok, notes = _fact_valid(fact, market)
        check = checks.get(metric)
        check_ok = True
        if metric in MANDATORY_CROSS_CHECK:
            if check is None:
                check_ok = False
                notes.append("No independent cross-check")
                discrepancies.append(
                    CrossCheck(
                        metric=metric,
                        primary_value=market.price if market else (fact.value if fact else None),
                        primary_source_id=market.source_id if market else (fact.source_id if fact else None),
                        classification=DiscrepancyClass.unresolved,
                        explanation="No independent cross-check from a different origin.",
                        passed=False,
                    )
                )
            else:
                discrepancies.append(check)
                if not check.passed:
                    check_ok = False
                    notes.append(check.explanation or "Cross-check failed")

        valid = ok and check_ok if metric in MANDATORY_CROSS_CHECK else ok
        # Metadata fields 10-12 have no mandatory cross-check.
        fields.append(
            FieldResult(
                metric=metric,
                value=market.price if market else (fact.value if fact else None),
                unit=market.currency if market else (fact.unit if fact else None),
                currency=market.currency if market else (fact.currency if fact else None),
                period_label=_period_label(fact, market),
                source_id=market.source_id if market else (fact.source_id if fact else None),
                cross_check_source_id=check.cross_check_source_id if check else None,
                cross_check_value=check.cross_check_value if check else None,
                difference=check.difference if check else None,
                status=FieldStatus.valid if valid else FieldStatus.failed if (fact or market) else FieldStatus.missing,
                notes=notes,
            )
        )

    valid_count = sum(1 for f in fields if f.status is FieldStatus.valid)
    findings = list(snapshot.notes)
    if valid_count < 11:
        findings.append(f"{snapshot.company.ticker} failed field validity ({valid_count}/12)")
    return CompanyValidation(
        ticker=snapshot.company.ticker,
        valid_count=valid_count,
        fields=fields,
        discrepancies=discrepancies,
        valuation=valuation,
        findings=findings,
    )


def compare_values(
    metric: str,
    primary: Decimal,
    primary_source_id: str,
    other: Decimal,
    other_source_id: str,
    explanation_if_fail: str,
    classification: DiscrepancyClass = DiscrepancyClass.unresolved,
) -> CrossCheck:
    diff = abs(primary - other)
    pct = _pct_diff(primary, other)
    passed = pct is not None and pct <= TOLERANCE
    return CrossCheck(
        metric=metric,
        primary_value=primary,
        primary_source_id=primary_source_id,
        cross_check_value=other,
        cross_check_source_id=other_source_id,
        difference=diff,
        difference_pct=pct,
        classification=None if passed else classification,
        explanation=None if passed else explanation_if_fail,
        passed=passed,
    )
