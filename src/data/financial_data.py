from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from data.config import load_xbrl_concepts
from data.hashing import content_hash, stable_id
from data.models import ClaimType, Company, FinancialFact, PeriodType, Source
from data.xbrl import (
    latest_annual,
    latest_instant,
    pick_concept,
    quarter_series,
)


REQUIRED_FLOW_METRICS = (
    "revenue",
    "operating_income",
    "net_income",
    "operating_cash_flow",
    "capex",
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _unit_for(unit_kind: str, currency: str) -> str:
    return "shares" if unit_kind == "shares" else currency


def _make_fact(
    *,
    company: Company,
    metric: str,
    value: Decimal,
    unit: str,
    currency: str | None,
    period_type: PeriodType,
    definition: str,
    source: Source,
    claim_type: ClaimType,
    period_start=None,
    period_end=None,
    as_of=None,
    formula: str | None = None,
    input_fact_ids: list[str] | None = None,
    concept: str | None = None,
    accession: str | None = None,
    source_date=None,
) -> FinancialFact:
    retrieved = source.retrieved_at
    payload = {
        "ticker": company.ticker,
        "metric": metric,
        "value": value,
        "unit": unit,
        "currency": currency,
        "period_type": period_type.value,
        "period_start": period_start,
        "period_end": period_end,
        "as_of": as_of,
        "concept": concept,
        "source_id": source.source_id,
    }
    digest = content_hash(payload)
    fact_id = stable_id(company.ticker, metric, period_type.value, str(period_end or as_of), source.source_id, digest[:12])
    return FinancialFact(
        fact_id=fact_id,
        metric=metric,
        value=value,
        unit=unit,
        currency=currency,
        period_type=period_type,
        period_start_date=period_start,
        period_end_date=period_end,
        as_of_date=as_of,
        listing=company.listing,
        definition=definition.strip(),
        source_id=source.source_id,
        source_date=source_date,
        retrieved_at=retrieved,
        content_hash=digest,
        claim_type=claim_type,
        formula=formula,
        input_fact_ids=input_fact_ids or [],
        concept=concept,
        accession=accession,
    )


def _quarter_facts(
    company: Company,
    metric: str,
    definition: str,
    source: Source,
    unit: str,
    currency: str | None,
    quarters: list[QuarterAmount],
) -> list[FinancialFact]:
    facts: list[FinancialFact] = []
    for quarter in quarters:
        claim = ClaimType.computed if quarter.derived else ClaimType.reported
        formula = None
        if quarter.derived:
            formula = quarter.formula or "derived from YTD or annual figures"
        facts.append(
            _make_fact(
                company=company,
                metric=metric,
                value=quarter.value,
                unit=unit,
                currency=currency,
                period_type=PeriodType.quarterly,
                definition=definition,
                source=source,
                claim_type=claim,
                period_start=quarter.start,
                period_end=quarter.end,
                formula=formula,
                concept=quarter.concept,
                accession=quarter.accession,
                source_date=quarter.end,
            )
        )
    return facts


def _ttm_fact(
    company: Company,
    metric: str,
    definition: str,
    source: Source,
    unit: str,
    currency: str | None,
    quarter_facts: list[FinancialFact],
) -> FinancialFact | None:
    if len(quarter_facts) < 4:
        return None
    last4 = quarter_facts[-4:]
    return _make_fact(
        company=company,
        metric=metric,
        value=sum((f.value for f in last4), Decimal("0")),
        unit=unit,
        currency=currency,
        period_type=PeriodType.ttm,
        definition=definition + " TTM is the sum of the last four reported (or derived) quarters.",
        source=source,
        claim_type=ClaimType.computed,
        period_start=last4[0].period_start_date,
        period_end=last4[-1].period_end_date,
        formula="sum(latest_4_reported_quarters)",
        input_fact_ids=[f.fact_id for f in last4],
        concept=last4[-1].concept,
        source_date=last4[-1].period_end_date,
    )


def extract_financial_facts(
    company: Company,
    companyfacts: dict[str, Any],
    source: Source,
    concept_config: dict[str, Any] | None = None,
) -> tuple[list[FinancialFact], list[str]]:
    config = concept_config or load_xbrl_concepts()
    allowed_forms = config["allowed_forms"]
    notes: list[str] = []
    facts: list[FinancialFact] = []
    metrics: dict[str, Any] = config["metrics"]

    chosen: dict[str, tuple[str, str]] = {}
    observations = {}
    for name, spec in metrics.items():
        picked = pick_concept(
            companyfacts,
            spec["candidates"],
            allowed_forms,
            spec["unit"],
            company.reporting_currency,
        )
        if picked is None:
            if not spec.get("optional"):
                notes.append(f"No XBRL observations for required metric {name}")
            continue
        taxonomy, concept, obs = picked
        chosen[name] = (taxonomy, concept)
        observations[name] = obs
        notes.append(f"{name}: using {taxonomy}:{concept} ({len(obs)} unique periods)")

    for name in REQUIRED_FLOW_METRICS:
        spec = metrics[name]
        if name not in observations:
            continue
        unit = _unit_for(spec["unit"], company.reporting_currency)
        quarters = quarter_series(observations[name], 4)
        if len(quarters) < 4:
            notes.append(f"{name}: only {len(quarters)} standalone quarters after YTD expansion")
        q_facts = _quarter_facts(company, name, spec["definition"], source, unit, company.reporting_currency, quarters)
        facts.extend(q_facts)
        ttm = _ttm_fact(company, name, spec["definition"], source, unit, company.reporting_currency, q_facts)
        if ttm:
            facts.append(ttm)
        annual_obs = latest_annual(observations[name])
        if annual_obs and annual_obs.start:
            facts.append(
                _make_fact(
                    company=company,
                    metric=name,
                    value=annual_obs.value,
                    unit=unit,
                    currency=company.reporting_currency,
                    period_type=PeriodType.annual,
                    definition=spec["definition"] + " Latest fiscal-year figure, secondary cross-check only.",
                    source=source,
                    claim_type=ClaimType.reported,
                    period_start=annual_obs.start,
                    period_end=annual_obs.end,
                    concept=annual_obs.concept,
                    accession=annual_obs.accession,
                    source_date=annual_obs.filed,
                )
            )

    def add_instant(metric_name: str, as_metric: str | None = None) -> FinancialFact | None:
        spec = metrics[metric_name]
        if metric_name not in observations:
            return None
        obs = latest_instant(observations[metric_name])
        if obs is None:
            return None
        unit = _unit_for(spec["unit"], company.reporting_currency)
        currency = None if spec["unit"] == "shares" else company.reporting_currency
        fact = _make_fact(
            company=company,
            metric=as_metric or metric_name,
            value=obs.value,
            unit=unit,
            currency=currency,
            period_type=PeriodType.point_in_time,
            definition=spec["definition"],
            source=source,
            claim_type=ClaimType.reported,
            as_of=obs.end,
            period_end=obs.end,
            concept=obs.concept,
            accession=obs.accession,
            source_date=obs.filed,
        )
        facts.append(fact)
        return fact

    ttm_ocf = next((f for f in facts if f.metric == "operating_cash_flow" and f.period_type is PeriodType.ttm), None)
    ttm_capex = next((f for f in facts if f.metric == "capex" and f.period_type is PeriodType.ttm), None)
    if ttm_ocf and ttm_capex:
        facts.append(
            _make_fact(
                company=company,
                metric="fcf",
                value=ttm_ocf.value - ttm_capex.value,
                unit=company.reporting_currency,
                currency=company.reporting_currency,
                period_type=PeriodType.ttm,
                definition="Free cash flow = TTM operating cash flow − TTM capex. Never taken from a provider.",
                source=source,
                claim_type=ClaimType.computed,
                period_start=ttm_ocf.period_start_date,
                period_end=ttm_ocf.period_end_date,
                formula="operating_cash_flow_ttm - capex_ttm",
                input_fact_ids=[ttm_ocf.fact_id, ttm_capex.fact_id],
            )
        )

    cash = add_instant("cash")
    sti = add_instant("short_term_investments")
    noncurrent = add_instant("long_term_debt_noncurrent")
    current = add_instant("long_term_debt_current")
    reported_debt = add_instant("long_term_debt_total")
    leases = add_instant("operating_lease_liability")
    shares = add_instant("shares_outstanding")
    cover = add_instant("shares_outstanding_cover", as_metric="shares_outstanding_cover")
    latest_bs = max(
        (f.as_of_date for f in (cash, noncurrent, current, reported_debt) if f and f.as_of_date),
        default=None,
    )
    if shares is None or (latest_bs and shares.as_of_date and shares.as_of_date < latest_bs):
        if cover is not None:
            notes.append(
                "period-end CommonStockSharesOutstanding is missing or stale versus the latest "
                "balance-sheet date; using cover-page DEI shares. as_of is the cover date, not period-end."
            )
            # Promote cover-page shares to the required metric while keeping the stale
            # period-end figure in the snapshot for comparison.
            promoted = cover.model_copy(
                update={
                    "metric": "shares_outstanding",
                    "definition": (
                        "Cover-page common shares outstanding "
                        "(dei:EntityCommonStockSharesOutstanding). Not the fiscal period-end figure."
                    ),
                }
            )
            facts.append(promoted)
            shares = promoted
        elif shares is None:
            notes.append("shares_outstanding missing")

    debt_inputs: list[FinancialFact] = []
    debt_value: Decimal | None = None
    formula = None
    if current and noncurrent and current.as_of_date == noncurrent.as_of_date:
        debt_value = current.value + noncurrent.value
        debt_inputs = [current, noncurrent]
        formula = "long_term_debt_current + long_term_debt_noncurrent"
        if reported_debt and reported_debt.as_of_date == current.as_of_date:
            if reported_debt.value == debt_value:
                notes.append("Reported LongTermDebt equals current + noncurrent; using the sum of components")
            else:
                notes.append(
                    f"Reported LongTermDebt {reported_debt.value} differs from current+noncurrent {debt_value}"
                )
    elif reported_debt:
        debt_value = reported_debt.value
        debt_inputs = [reported_debt]
        formula = "reported long_term_debt"
        notes.append("total_debt uses reported LongTermDebt; component split was incomplete")
    elif noncurrent:
        debt_value = noncurrent.value
        debt_inputs = [noncurrent]
        formula = "long_term_debt_noncurrent only"
        notes.append("total_debt uses noncurrent debt only; current portion missing")

    if debt_value is not None and debt_inputs:
        facts.append(
            _make_fact(
                company=company,
                metric="total_debt",
                value=debt_value,
                unit=company.reporting_currency,
                currency=company.reporting_currency,
                period_type=PeriodType.point_in_time,
                definition=(
                    "Interest-bearing debt: current portion of long-term debt plus noncurrent "
                    "long-term debt. Operating lease liabilities are excluded and stored separately."
                ),
                source=source,
                claim_type=ClaimType.computed,
                as_of=debt_inputs[0].as_of_date,
                period_end=debt_inputs[0].as_of_date,
                formula=formula,
                input_fact_ids=[f.fact_id for f in debt_inputs],
                source_date=debt_inputs[0].source_date,
            )
        )
    if leases:
        notes.append(f"Operating lease liability {leases.value} excluded from total_debt")
    if cash and sti and cash.as_of_date != sti.as_of_date:
        notes.append(
            f"Cash as_of {cash.as_of_date} does not match short-term investments as_of {sti.as_of_date}"
        )

    # Metadata facts 10-12
    latest_ttm = max(
        (f for f in facts if f.period_type is PeriodType.ttm),
        key=lambda f: f.period_end_date or f.as_of_date,
        default=None,
    )
    latest_annual_fact = max(
        (f for f in facts if f.period_type is PeriodType.annual),
        key=lambda f: f.period_end_date or f.as_of_date,
        default=None,
    )
    facts.append(
        _make_fact(
            company=company,
            metric="reporting_currency",
            value=Decimal("1"),
            unit=company.reporting_currency,
            currency=company.reporting_currency,
            period_type=PeriodType.point_in_time,
            definition="ISO currency code of the company's reporting currency.",
            source=source,
            claim_type=ClaimType.reported,
            as_of=(latest_ttm.period_end_date if latest_ttm else _now().date()),
            formula=None,
        )
    )
    # reporting_currency is metadata; the numeric 1 is a placeholder so the model stays numeric.
    facts[-1] = facts[-1].model_copy(
        update={
            "definition": f"Reporting currency is {company.reporting_currency}.",
            "unit": company.reporting_currency,
        }
    )
    fiscal_label = []
    if latest_ttm and latest_ttm.period_end_date:
        fiscal_label.append(f"latest TTM end {latest_ttm.period_end_date.isoformat()}")
    if latest_annual_fact and latest_annual_fact.period_end_date:
        fiscal_label.append(
            f"latest FY {latest_annual_fact.period_start_date} to {latest_annual_fact.period_end_date}"
        )
    if not latest_ttm:
        notes.append("Could not build trailing-twelve-month totals (need four quarters). Annual figures alone are not enough.")
    as_of_meta = (
        (latest_ttm.period_end_date if latest_ttm else None)
        or (latest_annual_fact.period_end_date if latest_annual_fact else None)
        or _now().date()
    )
    facts.append(
        _make_fact(
            company=company,
            metric="fiscal_period",
            value=Decimal(str(as_of_meta.toordinal())),
            unit="date_ordinal",
            currency=None,
            period_type=PeriodType.point_in_time,
            definition="; ".join(fiscal_label) or "Fiscal period labels unavailable",
            source=source,
            claim_type=ClaimType.reported,
            as_of=as_of_meta,
        )
    )
    facts.append(
        _make_fact(
            company=company,
            metric="listing",
            value=Decimal("1"),
            unit=company.listing,
            currency=company.valuation_currency,
            period_type=PeriodType.point_in_time,
            definition=f"Valuation listing {company.listing} on {company.exchange}. ADR/other listings are not mixed in.",
            source=source,
            claim_type=ClaimType.reported,
            as_of=as_of_meta,
        )
    )
    return facts, notes
