from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from data.financial_data import _make_fact
from data.http import client as http_client
from data.models import ClaimType, Company, FinancialFact, PeriodType, Source
from data.snapshots import SnapshotStore

FILINGS_URL = "https://filings.xbrl.org/api/filings"
FILINGS_HOST = "https://filings.xbrl.org"

# Concepts on a European yearly report. Extra breakdowns (by country, by product)
# are ignored. A fact is kept only when it has no breakdown attached.
ANNUAL = {
    "ifrs-full:RevenueFromContractsWithCustomers": "revenue",
    "ifrs-full:ProfitLoss": "net_income",
    "ifrs-full:ProfitLossFromOperatingActivities": "operating_income",
    "ifrs-full:CashFlowsFromUsedInOperatingActivities": "operating_cash_flow",
    "ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities": "capex",
}
INSTANT = {
    "ifrs-full:CashAndCashEquivalents": "cash",
    "ifrs-full:NumberOfSharesOutstanding": "shares_outstanding",
}
DEBT_PARTS = {
    "ifrs-full:CurrentPortionOfLongtermBorrowings": "current",
    "ifrs-full:LongtermBorrowings": "noncurrent",
}
_BARE_DIMENSIONS = {"concept", "entity", "period", "unit"}


class EuropeEsefProvider:
    """European electronic-report library. Yearly packages, not a quarterly feed."""

    origin = "europe_esef"

    def __init__(self, timeout: float = 60.0) -> None:
        self.timeout = timeout

    def fetch_financials(
        self, company: Company, store: SnapshotStore
    ) -> tuple[list[FinancialFact], list[Source], list[str]]:
        notes = [
            "Home-market source: the public European electronic-report library. "
            "The United States filing cabinet was not used for these yearly figures."
        ]
        with http_client(
            {"User-Agent": "Epilith/0.1", "Accept": "application/vnd.api+json, application/json"},
            self.timeout,
        ) as http:
            response = http.get(FILINGS_URL, params={"filter[entity.name]": company.name, "page[size]": "5"})
            response.raise_for_status()
            content = response.content
            source = store.save_raw(
                origin=self.origin,
                ticker=company.ticker,
                filename="filings.json",
                content=content,
                url=FILINGS_URL,
                name="European electronic filings search",
                metadata={"query_name": company.name},
            )
            payload = response.json()
            count = (payload.get("meta") or {}).get("count", len(payload.get("data") or []))
            notes.append(
                f"European library search for '{company.name}' returned {count} yearly package(s). "
                "It does not publish the last four quarters."
            )
            latest = _latest_filing(payload)
            if latest is None:
                notes.append("No European yearly package was matched for this company name.")
                return [], [source], notes
            json_path = (latest.get("attributes") or {}).get("json_url")
            if not json_path:
                notes.append("The latest European package did not include a facts file.")
                return [], [source], notes
            facts_url = json_path if str(json_path).startswith("http") else FILINGS_HOST + str(json_path)
            facts_response = http.get(facts_url)
            facts_response.raise_for_status()
        facts_source = store.save_raw(
            origin=self.origin,
            ticker=company.ticker,
            filename="annual_facts.json",
            content=facts_response.content,
            url=facts_url,
            name="European yearly report facts",
            metadata={"period_end": (latest.get("attributes") or {}).get("period_end")},
        )
        built, fact_notes = facts_from_esef_json(
            company, facts_source, facts_response.json()
        )
        notes.extend(fact_notes)
        return built, [source, facts_source], notes


def facts_from_esef_json(
    company: Company, source: Source, payload: dict
) -> tuple[list[FinancialFact], list[str]]:
    notes: list[str] = []
    annual: dict[str, tuple[date, date, Decimal]] = {}
    instant: dict[str, tuple[date, Decimal]] = {}
    debt: dict[str, tuple[date, Decimal]] = {}
    currency = company.reporting_currency.upper()
    for fact in (payload.get("facts") or {}).values():
        dims = fact.get("dimensions") or {}
        if set(dims) - _BARE_DIMENSIONS:
            continue
        concept = dims.get("concept") or ""
        unit = str(dims.get("unit") or "")
        value = fact.get("value")
        if value in (None, "", 0, 0.0, "0", "0.0"):
            continue
        amount = Decimal(str(value))
        if amount == 0:
            continue
        kind, start, end = _period_bounds(str(dims.get("period") or ""))
        if kind == "duration" and concept in ANNUAL and start and end:
            if not unit.endswith(currency):
                continue
            metric = ANNUAL[concept]
            annual[metric] = (start, end, abs(amount) if metric == "capex" else amount)
        elif kind == "instant" and end and concept in INSTANT:
            metric = INSTANT[concept]
            if metric == "shares_outstanding":
                if "shares" not in unit:
                    continue
            elif not unit.endswith(currency):
                continue
            instant[metric] = (end, amount)
        elif kind == "instant" and end and concept in DEBT_PARTS and unit.endswith(currency):
            debt[DEBT_PARTS[concept]] = (end, amount)
    built: list[FinancialFact] = []
    for metric, (start, end, value) in annual.items():
        built.append(
            _make_fact(
                company=company,
                metric=metric,
                value=value,
                unit="shares" if metric == "shares_outstanding" else currency,
                currency=None if metric == "shares_outstanding" else currency,
                period_type=PeriodType.annual,
                definition=(
                    f"Full-year {metric.replace('_', ' ')} from the European yearly report, "
                    f"for the year ending {end.isoformat()}."
                ),
                source=source,
                claim_type=ClaimType.reported,
                period_start=start,
                period_end=end,
                concept=metric,
                source_date=end,
            )
        )
    for metric, (as_of, value) in instant.items():
        built.append(
            _make_fact(
                company=company,
                metric=metric,
                value=value,
                unit="shares" if metric == "shares_outstanding" else currency,
                currency=None if metric == "shares_outstanding" else currency,
                period_type=PeriodType.point_in_time,
                definition=(
                    "Shares in issue from the European yearly report."
                    if metric == "shares_outstanding"
                    else "Cash and cash equivalents from the European yearly report. Short-term investments are not included."
                ),
                source=source,
                claim_type=ClaimType.reported,
                as_of=as_of,
                concept=metric,
                source_date=as_of,
            )
        )
    if "current" in debt and "noncurrent" in debt and debt["current"][0] == debt["noncurrent"][0]:
        as_of = debt["current"][0]
        for metric, key, label in (
            ("debt_current", "current", "Borrowings due within a year from the European yearly report."),
            ("debt_noncurrent", "noncurrent", "Long-term borrowings from the European yearly report."),
        ):
            built.append(
                _make_fact(
                    company=company,
                    metric=metric,
                    value=debt[key][1],
                    unit=currency,
                    currency=currency,
                    period_type=PeriodType.point_in_time,
                    definition=label,
                    source=source,
                    claim_type=ClaimType.reported,
                    as_of=as_of,
                    concept=metric,
                    source_date=as_of,
                )
            )
        built.append(
            _make_fact(
                company=company,
                metric="total_debt",
                value=debt["current"][1] + debt["noncurrent"][1],
                unit=currency,
                currency=currency,
                period_type=PeriodType.point_in_time,
                definition=(
                    "Borrowings from the European yearly report: the portion due within a year "
                    "plus long-term borrowings. Lease liabilities are not included."
                ),
                source=source,
                claim_type=ClaimType.computed,
                as_of=as_of,
                formula="current_borrowings + long_term_borrowings",
                source_date=as_of,
            )
        )
    if built:
        notes.append(
            "The latest European yearly report was read. "
            "Its full-year figures are a second document, not a substitute for the quarterly statement."
        )
    else:
        notes.append("The European yearly report did not yield any of the tracked lines.")
    return built, notes


def _latest_filing(payload: dict) -> dict | None:
    rows = payload.get("data") or []
    dated = [row for row in rows if (row.get("attributes") or {}).get("period_end")]
    if not dated:
        return None
    return max(dated, key=lambda row: row["attributes"]["period_end"])


def _period_bounds(period: str) -> tuple[str, date | None, date | None]:
    if not period:
        return "none", None, None
    if "/" in period:
        start_text, end_text = period.split("/", 1)
        return "duration", _day(start_text, exclusive=False), _day(end_text, exclusive=True)
    return "instant", None, _day(period, exclusive=True)


def _day(text: str, exclusive: bool) -> date:
    day = date.fromisoformat(text[:10])
    if exclusive and "T00:00:00" in text:
        return day - timedelta(days=1)
    return day
