from __future__ import annotations

from datetime import date
from decimal import Decimal

from data.financial_data import _make_fact, _ttm_fact
from data.models import ClaimType, Company, FinancialFact, PeriodType, Source
from data.statement_table import StatedAmount, collapse_amounts

FLOW_METRICS = (
    "revenue",
    "operating_income",
    "net_income",
    "operating_cash_flow",
    "capex",
)

FLOW_DEFINITIONS = {
    "revenue": "Sales for one quarter, read from the company's own quarterly report.",
    "operating_income": "Operating profit for one quarter, read from the company's own quarterly report.",
    "net_income": "Profit belonging to the parent company's shareholders for one quarter, read from the company's own quarterly report.",
    "operating_cash_flow": "Cash from running the business for one quarter, read from the company's own quarterly report.",
    "capex": "Purchases of property and equipment for one quarter, read from the company's own quarterly report. The amount is stored as a positive number.",
}


def build_missing_facts(
    company: Company,
    existing: list[FinancialFact],
    amounts: list[StatedAmount],
    sources_by_id: dict[str, Source],
) -> tuple[list[FinancialFact], list[str]]:
    """Fill lines the home-market feed did not publish, using the company report."""
    notes: list[str] = []
    built: list[FinancialFact] = []
    have = {fact.metric for fact in existing}
    # A full-year figure is not a substitute for the four quarters.
    have_flows = {
        fact.metric
        for fact in existing
        if fact.period_type in {PeriodType.quarterly, PeriodType.ttm}
    }

    for metric in FLOW_METRICS:
        if metric in have_flows:
            continue
        quarters = collapse_amounts(amounts, metric, "quarter")
        if len(quarters) < 4:
            continue
        quarter_facts: list[FinancialFact] = []
        for item in quarters:
            source = sources_by_id.get(item.source_id)
            if source is None or item.start is None:
                continue
            quarter_facts.append(
                _make_fact(
                    company=company,
                    metric=metric,
                    value=item.value,
                    unit=company.reporting_currency,
                    currency=company.reporting_currency,
                    period_type=PeriodType.quarterly,
                    definition=FLOW_DEFINITIONS[metric],
                    source=source,
                    claim_type=ClaimType.reported,
                    period_start=item.start,
                    period_end=item.end,
                    source_date=item.end,
                )
            )
        aligned = _align_to_existing_window(quarter_facts, existing)
        if len(aligned) < 4:
            continue
        built.extend(quarter_facts)
        latest_source = sources_by_id.get(aligned[-1].source_id)
        if latest_source is None:
            continue
        ttm = _ttm_fact(
            company,
            metric,
            FLOW_DEFINITIONS[metric],
            latest_source,
            company.reporting_currency,
            company.reporting_currency,
            aligned,
        )
        if ttm is not None:
            built.append(ttm)
        notes.append(
            f"{metric.replace('_', ' ')} was missing from the home-market feed, "
            "so the company's quarterly report supplied the last four quarters."
        )

    if "cash" not in have:
        cash_rows = collapse_amounts(amounts, "cash", "instant")
        if cash_rows:
            item = cash_rows[-1]
            source = sources_by_id.get(item.source_id)
            if source is not None:
                built.append(_point(company, "cash", item.value, item.end, source, "Cash and cash equivalents from the company's quarterly report. Short-term investments are not included."))
                notes.append("Cash was missing from the home-market feed, so the company report supplied it.")

    if "total_debt" not in have:
        debt_rows = collapse_amounts(amounts, "total_debt", "instant")
        if debt_rows:
            item = debt_rows[-1]
            source = sources_by_id.get(item.source_id)
            if source is not None:
                both = item.priority >= 2
                built.append(
                    _make_fact(
                        company=company,
                        metric="total_debt",
                        value=item.value,
                        unit=company.reporting_currency,
                        currency=company.reporting_currency,
                        period_type=PeriodType.point_in_time,
                        definition=(
                            "Borrowings from the company's quarterly report: the current portion that is labeled as bonds or bank loans, plus long-term bonds or long-term debt. Other liabilities are excluded."
                            if both
                            else "Long-term borrowings from the company's quarterly report. That report did not list a separate current portion, so this is not a complete debt total."
                        ),
                        source=source,
                        claim_type=ClaimType.computed if both else ClaimType.reported,
                        as_of=item.end,
                        formula="current_borrowings + long_term_borrowings" if both else None,
                        source_date=item.end,
                    )
                )
                notes.append(
                    "Debt was taken from the company report."
                    if both
                    else "Debt was taken from the long-term line in the company report because no separate current portion was listed."
                )

    if built and "reporting_currency" not in have:
        anchor = max((fact.period_end_date or fact.as_of_date or date.today() for fact in built))
        source = built[0] and sources_by_id.get(built[0].source_id)
        if source is not None:
            built.extend(_identity(company, source, anchor))
    return built, notes


def _align_to_existing_window(quarter_facts: list[FinancialFact], existing: list[FinancialFact]) -> list[FinancialFact]:
    """Keep a filled total on the same end date as figures the home feed already has."""
    ends = [fact.period_end_date for fact in existing if fact.period_type is PeriodType.ttm and fact.period_end_date]
    if not ends:
        return quarter_facts[-4:]
    end_on = max(ends)
    eligible = [
        fact
        for fact in quarter_facts
        if fact.period_end_date and (fact.period_end_date <= end_on or abs((fact.period_end_date - end_on).days) <= 5)
    ]
    if not eligible or abs((eligible[-1].period_end_date - end_on).days) > 5:
        return []
    return eligible[-4:]


def _point(company: Company, metric: str, value: Decimal, as_of: date, source: Source, definition: str) -> FinancialFact:
    return _make_fact(
        company=company,
        metric=metric,
        value=value,
        unit=company.reporting_currency,
        currency=company.reporting_currency,
        period_type=PeriodType.point_in_time,
        definition=definition,
        source=source,
        claim_type=ClaimType.reported,
        as_of=as_of,
        source_date=as_of,
    )


def _identity(company: Company, source: Source, as_of: date) -> list[FinancialFact]:
    return [
        _make_fact(
            company=company,
            metric="reporting_currency",
            value=Decimal("1"),
            unit=company.reporting_currency,
            currency=company.reporting_currency,
            period_type=PeriodType.point_in_time,
            definition=f"Reporting currency is {company.reporting_currency}.",
            source=source,
            claim_type=ClaimType.reported,
            as_of=as_of,
        ),
        _make_fact(
            company=company,
            metric="fiscal_period",
            value=Decimal(str(as_of.toordinal())),
            unit="date_ordinal",
            currency=None,
            period_type=PeriodType.point_in_time,
            definition=f"Latest period end in the company report is {as_of.isoformat()}.",
            source=source,
            claim_type=ClaimType.reported,
            as_of=as_of,
        ),
        _make_fact(
            company=company,
            metric="listing",
            value=Decimal("1"),
            unit=company.listing,
            currency=company.valuation_currency,
            period_type=PeriodType.point_in_time,
            definition=f"Valuation listing {company.listing} on {company.exchange}.",
            source=source,
            claim_type=ClaimType.reported,
            as_of=as_of,
        ),
    ]
