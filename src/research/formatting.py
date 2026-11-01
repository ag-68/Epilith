from __future__ import annotations

from datetime import date
from decimal import Decimal

from research.models import FactLine, FactSheet

METRIC_LABELS = {
    "revenue": "Revenue",
    "operating_income": "Operating income",
    "net_income": "Net income",
    "operating_cash_flow": "Operating cash flow",
    "capex": "Capex",
    "total_debt": "Total debt",
    "cash": "Cash and equivalents",
    "shares_outstanding": "Shares outstanding",
    "price": "Price",
    "reporting_currency": "Reporting currency",
    "fiscal_period": "Latest fiscal period end",
    "listing": "Listing",
}

VALUATION_LABELS = {
    "market_cap": "Market cap",
    "enterprise_value": "Enterprise value",
    "trailing_pe": "Trailing P/E",
    "ev_sales": "EV / Sales",
    "fcf": "Free cash flow (TTM, computed)",
    "fcf_yield": "FCF yield",
    "ttm_end_date": "TTM period end",
    "balance_sheet_as_of": "Balance sheet as of",
}


def human_amount(value: Decimal, currency: str | None) -> str:
    magnitude = abs(value)
    if magnitude >= Decimal("1e12"):
        text = f"{value / Decimal('1e12'):,.2f} trillion"
    elif magnitude >= Decimal("1e9"):
        text = f"{value / Decimal('1e9'):,.2f} billion"
    elif magnitude >= Decimal("1e6"):
        text = f"{value / Decimal('1e6'):,.1f} million"
    else:
        text = f"{value:,.2f}"
    return f"{currency} {text}" if currency else text


def fact_value_text(line: FactLine) -> str:
    if line.metric == "reporting_currency":
        return line.unit or ""
    if line.metric == "listing":
        return line.unit or ""
    if line.metric == "fiscal_period":
        return date.fromordinal(int(line.value)).isoformat()
    if line.metric == "shares_outstanding":
        return f"{line.value / Decimal('1e9'):,.3f} billion shares"
    if line.metric == "price":
        return f"{line.currency} {line.value:,.2f}"
    return human_amount(line.value, line.currency)


def confirmation_text(line: FactLine) -> str:
    """Where the figure comes from and whether a second document agrees, in a few words."""
    origin = {
        "authority": "regulator filing",
        "company": "company release",
        "market": "market quote",
    }.get(line.provenance or "", line.provenance or "source unknown")
    agreement = {
        "confirmed": "confirmed by a second document",
        "explained": "second document differs for a documented reason",
        "disputed": "second document disagrees, unexplained",
        "unconfirmed": "no second document",
    }.get(line.confirmation, line.confirmation)
    return f"{origin}; {agreement}"


def valuation_value_text(key: str, raw: str) -> str:
    if key in {"ttm_end_date", "balance_sheet_as_of"}:
        return raw
    value = Decimal(raw)
    if key in {"market_cap", "enterprise_value", "fcf"}:
        return human_amount(value, None)
    if key == "fcf_yield":
        return f"{value * 100:.2f}%"
    return f"{value:.1f}x"


def fact_sheet_text(sheet: FactSheet) -> str:
    """Plain text table of the validated facts, as given to the models and printed in the memo."""
    lines = [
        f"Company: {sheet.company_name} ({sheet.ticker}), listing {sheet.listing}, figures in {sheet.currency}.",
        f"Facts come from Experiment 0a report {sheet.report_path}, data snapshot {sheet.data_snapshot_id}.",
        "",
    ]
    for line in sheet.facts:
        label = METRIC_LABELS.get(line.metric, line.metric)
        lines.append(f"- {label}: {fact_value_text(line)} [{line.period_label or 'n/a'}; {confirmation_text(line)}]")
    if sheet.excluded:
        lines.append("")
        lines.append("Not validated in 0a (do not rely on these):")
        for line in sheet.excluded:
            label = METRIC_LABELS.get(line.metric, line.metric)
            lines.append(f"- {label}: {fact_value_text(line)} [{line.period_label or 'n/a'}] status={line.status}")
    if sheet.valuation:
        lines.append("")
        lines.append(f"Descriptive valuation panel ({sheet.currency}), computed in Python from the facts above:")
        for key, raw in sheet.valuation.items():
            lines.append(f"- {VALUATION_LABELS.get(key, key)}: {valuation_value_text(key, raw)}")
        for note in sheet.valuation_notes:
            lines.append(f"  Note: {note}")
    return "\n".join(lines)
