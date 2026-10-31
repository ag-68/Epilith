from __future__ import annotations

from decimal import Decimal, InvalidOperation

from data.models import FinancialSnapshot, PeriodType, ValuationPanel
from validation.data_quality import home_flow_fact


def _div(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    if numerator is None or denominator in {None, Decimal("0")}:
        return None
    try:
        return numerator / denominator
    except InvalidOperation:
        return None


def compute_panel(snapshot: FinancialSnapshot) -> ValuationPanel:
    company = snapshot.company
    notes: list[str] = [
        "Descriptive evidence only. Trailing P/E is misleading for cyclical semiconductor companies.",
        "No forward P/E, DCF, reverse valuation, or scenario weighting in Experiment 0a.",
    ]
    ttm_rev = home_flow_fact(snapshot, "revenue")
    ttm_ni = home_flow_fact(snapshot, "net_income")
    ttm_ocf = home_flow_fact(snapshot, "operating_cash_flow")
    ttm_capex = home_flow_fact(snapshot, "capex")
    debt = snapshot.latest_fact("total_debt", PeriodType.point_in_time)
    cash = snapshot.latest_fact("cash", PeriodType.point_in_time)
    shares = snapshot.latest_fact("shares_outstanding", PeriodType.point_in_time)
    market = snapshot.market

    if ttm_rev is not None and ttm_rev.period_type is PeriodType.annual:
        notes.append(
            "The home-market filing publishes a full year, and the quarterly statement uses different accounting rules. "
            "Valuation uses the home-market full year."
        )
    fcf = None
    if ttm_ocf and ttm_capex:
        fcf = ttm_ocf.value - ttm_capex.value
        if ttm_ocf.period_type is PeriodType.annual:
            notes.append("FCF = full-year cash from the business − full-year equipment purchases. Provider FCF is not used.")
        else:
            notes.append("FCF = TTM operating cash flow − TTM capex. Provider FCF is not used.")

    market_cap = None
    if market and shares:
        market_cap = market.price * shares.value
        if shares.as_of_date and market.as_of_timestamp.date() != shares.as_of_date:
            notes.append(
                f"Market cap mixes price as of {market.as_of_timestamp.isoformat()} with shares as of {shares.as_of_date}."
            )

    enterprise_value = None
    if market_cap is not None and debt and cash:
        enterprise_value = market_cap + debt.value - cash.value
        if debt.as_of_date != cash.as_of_date:
            notes.append(f"EV mixes debt as of {debt.as_of_date} with cash as of {cash.as_of_date}.")

    ttm_end = ttm_rev.period_end_date if ttm_rev else None
    balance_as_of = cash.as_of_date if cash else (debt.as_of_date if debt else None)
    if ttm_end and balance_as_of and abs((balance_as_of - ttm_end).days) > 5:
        notes.append(
            f"The balance sheet is as of {balance_as_of.isoformat()} and the trailing figures run through {ttm_end.isoformat()}."
        )
    return ValuationPanel(
        listing=company.listing,
        currency=company.valuation_currency,
        market_cap=market_cap,
        enterprise_value=enterprise_value,
        trailing_pe=_div(market_cap, ttm_ni.value if ttm_ni else None),
        ev_sales=_div(enterprise_value, ttm_rev.value if ttm_rev else None),
        fcf=fcf,
        fcf_yield=_div(fcf, market_cap),
        price=market.price if market else None,
        shares_outstanding=shares.value if shares else None,
        total_debt=debt.value if debt else None,
        cash=cash.value if cash else None,
        ttm_revenue=ttm_rev.value if ttm_rev else None,
        ttm_net_income=ttm_ni.value if ttm_ni else None,
        ttm_operating_cash_flow=ttm_ocf.value if ttm_ocf else None,
        ttm_capex=ttm_capex.value if ttm_capex else None,
        price_as_of=market.as_of_timestamp if market else None,
        ttm_end_date=ttm_end,
        balance_sheet_as_of=cash.as_of_date if cash else (debt.as_of_date if debt else None),
        notes=notes,
    )
