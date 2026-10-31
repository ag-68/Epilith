from __future__ import annotations

import json
import re
from datetime import date
from decimal import Decimal
from html.parser import HTMLParser

from data.financial_data import _make_fact, _quarter_facts, _ttm_fact
from data.http import client as http_client
from data.models import ClaimType, Company, FinancialFact, PeriodType, Source
from data.periods import QuarterAmount
from data.snapshots import SnapshotStore

MOPS_DATA_URL = "https://mopsfin.twse.com.tw/compare/data"
MOPS_REPORT_URL = "https://mopsfin.twse.com.tw/compare/report"
PROFILE_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
THOUSANDS = Decimal("1000")

# Names used by the Taiwan public disclosure comparison site.
# Amounts on that feed are in thousands of Taiwan dollars.
FLOW_SERIES = {
    "revenue": (
        "Revenue",
        "Sales for one quarter, from the Taiwan public disclosure site. "
        "The feed reports thousands of Taiwan dollars; the stored value is Taiwan dollars.",
    ),
    "operating_income": (
        "OperatingIncome",
        "Operating profit for one quarter, from the Taiwan public disclosure site, in Taiwan dollars.",
    ),
    "net_income": (
        "NetProfit",
        "Net profit for one quarter, from the Taiwan public disclosure site, in Taiwan dollars. "
        "This series can include profit belonging to other shareholders, not only the parent company.",
    ),
    "operating_cash_flow": (
        "OperatingCashflow",
        "Cash from the business for one quarter, from the Taiwan public disclosure site, in Taiwan dollars.",
    ),
}

QUARTER_BOUNDS = {
    1: (date(1, 1, 1), date(1, 3, 31)),
    2: (date(1, 4, 1), date(1, 6, 30)),
    3: (date(1, 7, 1), date(1, 9, 30)),
    4: (date(1, 10, 1), date(1, 12, 31)),
}


class TwseMopsProvider:
    origin = "twse_mops"

    def __init__(self, timeout: float = 60.0) -> None:
        self.timeout = timeout

    def fetch_financials(
        self, company: Company, store: SnapshotStore
    ) -> tuple[list[FinancialFact], list[Source], list[str]]:
        code = company.local_code or company.ticker
        notes = [
            "Home-market source: Taiwan public disclosure site and the Taiwan exchange company profile. "
            "The United States filing cabinet was not used."
        ]
        if not code:
            return [], [], notes + ["Taiwan stock code is missing, so no filing was downloaded."]

        facts: list[FinancialFact] = []
        sources: list[Source] = []
        recent_labels: list[str] = []
        with http_client(
            {
                "User-Agent": "Mozilla/5.0 Epilith/0.1",
                "Accept": "application/json",
                "Referer": "https://mopsfin.twse.com.tw/",
            },
            self.timeout,
        ) as http:
            for metric, (item, definition) in FLOW_SERIES.items():
                response = http.post(
                    MOPS_DATA_URL,
                    data={
                        "companyId": code,
                        "compareItem": item,
                        "quarter": "true",
                        "ylabel": "仟元",
                        "ys": "0",
                        "revenue": "false",
                        "bcodeAvg": "false",
                        "companyAvg": "false",
                        "qnumber": "8",
                    },
                )
                response.raise_for_status()
                content = response.content
                source = store.save_raw(
                    origin=self.origin,
                    ticker=company.ticker,
                    filename=f"{item}.json",
                    content=content,
                    url=MOPS_DATA_URL,
                    name=f"Taiwan disclosure series {item}",
                    metadata={"company_code": code, "series": item},
                )
                sources.append(source)
                if not recent_labels:
                    recent_labels = [str(label) for label in (json.loads(content.decode("utf-8")).get("xaxisList") or [])][-6:]
                quarters = quarters_from_mops_series(content, concept=item)
                if len(quarters) < 4:
                    notes.append(f"{metric}: Taiwan series has {len(quarters)} quarters, need 4.")
                    continue
                quarter_facts = _quarter_facts(
                    company,
                    metric,
                    definition,
                    source,
                    company.reporting_currency,
                    company.reporting_currency,
                    quarters[-4:],
                )
                facts.extend(quarter_facts)
                ttm = _ttm_fact(
                    company,
                    metric,
                    definition,
                    source,
                    company.reporting_currency,
                    company.reporting_currency,
                    quarter_facts,
                )
                if ttm:
                    facts.append(ttm)

            profile_response = http.get(PROFILE_URL)
            profile_response.raise_for_status()
            profile_source = store.save_raw(
                origin="twse_openapi",
                ticker=company.ticker,
                filename="company_profile.json",
                content=profile_response.content,
                url=PROFILE_URL,
                name="Taiwan exchange company profile",
                metadata={"company_code": code},
            )
            sources.append(profile_source)
            profile_rows = profile_response.json()
            share_fact = _shares_fact(company, profile_source, profile_rows, code)
            if share_fact:
                facts.append(share_fact)
            else:
                notes.append("Issued share count was not in the Taiwan company profile.")
            par_fact = _par_fact(company, profile_source, profile_rows, code)
            if par_fact:
                facts.append(par_fact)
            statement_facts, statement_sources, statement_notes = _statement_facts(
                http, company, store, code, recent_labels
            )
            facts.extend(statement_facts)
            sources.extend(statement_sources)
            notes.extend(statement_notes)
        _append_identity_facts(company, facts, sources[0] if sources else profile_source)
        return facts, sources, notes


def quarters_from_mops_series(content: bytes, concept: str) -> list[QuarterAmount]:
    payload = json.loads(content.decode("utf-8"))
    graph = json.loads(payload["json"])["graphData"][0]["data"]
    labels = payload.get("xaxisList") or []
    quarters: list[QuarterAmount] = []
    for label, point in zip(labels, graph):
        if not isinstance(point, list) or len(point) < 2 or point[1] in (None, ""):
            continue
        start, end = quarter_bounds(str(label))
        quarters.append(
            QuarterAmount(
                start=start,
                end=end,
                value=Decimal(str(point[1])) * THOUSANDS,
                derived=False,
                concept=concept,
            )
        )
    return quarters


def standalone_from_cumulative(series: list[tuple[str, Decimal]]) -> list[QuarterAmount]:
    """Turn a year-to-date equipment-purchase line into single quarters.

    Taiwan's cash-flow statement is cumulative: the second quarter's figure
    includes the first quarter. Subtracting the earlier cumulative figure
    leaves the quarter on its own.
    """
    by_year: dict[int, dict[int, Decimal]] = {}
    for label, value in series:
        year_text, quarter_text = label.split("Q")
        by_year.setdefault(int(year_text), {})[int(quarter_text)] = value
    found: list[QuarterAmount] = []
    for year in sorted(by_year):
        quarters = by_year[year]
        for quarter in range(1, 5):
            if quarter not in quarters:
                continue
            start, end = quarter_bounds(f"{year}Q{quarter}")
            if quarter == 1:
                found.append(
                    QuarterAmount(start=start, end=end, value=quarters[1], derived=False, concept="ppe_purchases")
                )
                continue
            if quarter - 1 not in quarters:
                continue
            found.append(
                QuarterAmount(
                    start=start,
                    end=end,
                    value=quarters[quarter] - quarters[quarter - 1],
                    derived=True,
                    formula="cumulative cash flow minus the prior quarter's cumulative cash flow",
                    concept="ppe_purchases",
                )
            )
    return found


def _statement_facts(http, company: Company, store: SnapshotStore, code: str, labels: list[str]):
    notes: list[str] = []
    facts: list[FinancialFact] = []
    sources: list[Source] = []
    if not labels:
        notes.append("Taiwan's full statement was not requested because the quarterly series had no dates.")
        return facts, sources, notes
    capex_ytd: list[tuple[str, Decimal]] = []
    for label in labels:
        year_text, quarter_text = label.split("Q")
        try:
            html = _post_report(http, code, "CashflowStatement", f"{year_text}{quarter_text}")
        except Exception as exc:
            notes.append(f"Taiwan cash-flow statement for {label} was not read. {exc}")
            continue
        source = store.save_raw(
            origin="twse_mops",
            ticker=company.ticker,
            filename=f"cashflow_{label}.html",
            content=html,
            url=MOPS_REPORT_URL,
            name=f"Taiwan cash-flow statement {label}",
            metadata={"company_code": code, "period": label},
        )
        sources.append(source)
        rows = _report_rows(html.decode("utf-8", errors="replace"))
        purchase = _row_amount(rows, "取得不動產、廠房及設備")
        if purchase is not None:
            capex_ytd.append((label, abs(purchase) * THOUSANDS))
    quarters = standalone_from_cumulative(capex_ytd)
    if len(quarters) >= 4:
        definition = (
            "Purchases of property, plant and equipment from Taiwan's cumulative cash-flow statement, "
            "in Taiwan dollars. Each quarter after the first is the cumulative figure minus the prior quarter. "
            "The amount is stored as a positive number."
        )
        quarter_facts = _quarter_facts(
            company,
            "capex",
            definition,
            sources[-1],
            company.reporting_currency,
            company.reporting_currency,
            quarters[-4:],
        )
        facts.extend(quarter_facts)
        ttm = _ttm_fact(
            company,
            "capex",
            definition,
            sources[-1],
            company.reporting_currency,
            company.reporting_currency,
            quarter_facts,
        )
        if ttm:
            facts.append(ttm)
            notes.append("Equipment purchases were read from Taiwan's cash-flow statements and split into quarters.")
    else:
        notes.append("Taiwan's cash-flow statements did not yield four quarters of equipment purchases.")

    latest = labels[-1]
    year_text, quarter_text = latest.split("Q")
    try:
        html = _post_report(http, code, "BalanceSheet", f"{year_text}{quarter_text}")
    except Exception as exc:
        notes.append(f"Taiwan balance sheet for {latest} was not read. {exc}")
        return facts, sources, notes
    source = store.save_raw(
        origin="twse_mops",
        ticker=company.ticker,
        filename=f"balance_sheet_{latest}.html",
        content=html,
        url=MOPS_REPORT_URL,
        name=f"Taiwan balance sheet {latest}",
        metadata={"company_code": code, "period": latest},
    )
    sources.append(source)
    rows = _report_rows(html.decode("utf-8", errors="replace"))
    cash = _row_amount(rows, "現金及約當現金")
    _start, end = quarter_bounds(latest)
    if cash is not None:
        facts.append(
            _make_fact(
                company=company,
                metric="cash",
                value=cash * THOUSANDS,
                unit=company.reporting_currency,
                currency=company.reporting_currency,
                period_type=PeriodType.point_in_time,
                definition=(
                    "Cash and cash equivalents from Taiwan's balance-sheet statement. "
                    "Short-term investments are not included."
                ),
                source=source,
                claim_type=ClaimType.reported,
                as_of=end,
                source_date=end,
            )
        )
        notes.append(f"Cash was read from Taiwan's balance sheet for {latest}.")
    else:
        notes.append("Taiwan's balance sheet did not list cash and cash equivalents.")
    return facts, sources, notes


def _post_report(http, code: str, item: str, ys: str) -> bytes:
    response = http.post(
        MOPS_REPORT_URL,
        data={
            "companyId": code,
            "compareItem": item,
            "quarter": "true",
            "ylabel": "",
            "ys": ys,
            "revenue": "false",
            "bcodeAvg": "false",
            "companyAvg": "false",
            "qnumber": "4",
        },
        headers={"Referer": "https://mopsfin.twse.com.tw/"},
    )
    response.raise_for_status()
    if f'value="{ys[0:4]}Q{ys[-1]}"' not in response.text and f"{ys[0:4]}Q{ys[-1]}" not in response.text:
        raise ValueError(f"Taiwan statement did not come back for {ys}")
    return response.content


class _ReportTables(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(re.sub(r"\s+", "", "".join(self._cell)))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if any(self._row):
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def _report_rows(html: str) -> list[tuple[str, Decimal]]:
    parser = _ReportTables()
    parser.feed(html)
    if len(parser.tables) < 2:
        return []
    labels = [row[0] for row in parser.tables[0] if row]
    values = [row[0] for row in parser.tables[1] if row]
    rows: list[tuple[str, Decimal]] = []
    for label, raw in zip(labels, values):
        cleaned = raw.replace(",", "")
        if re.fullmatch(r"-?\d+(?:\.\d+)?", cleaned):
            rows.append((label, Decimal(cleaned)))
    return rows


def _row_amount(rows: list[tuple[str, Decimal]], label: str) -> Decimal | None:
    for name, value in rows:
        if name == label:
            return value
    return None


def _par_fact(company: Company, source: Source, rows: list[dict], code: str) -> FinancialFact | None:
    row = next((item for item in rows if str(item.get("公司代號")) == code), None)
    if row is None:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", str(row.get("普通股每股面額") or ""))
    if match is None:
        return None
    published = _roc_date(str(row.get("出表日期") or ""))
    return _make_fact(
        company=company,
        metric="par_value",
        value=Decimal(match.group(1)),
        unit=company.reporting_currency,
        currency=company.reporting_currency,
        period_type=PeriodType.point_in_time,
        definition=(
            "Face amount of one common share, as printed on the Taiwan exchange company profile. "
            "Capital stock divided by this face amount is a share count."
        ),
        source=source,
        claim_type=ClaimType.reported,
        as_of=published,
        concept="par_value",
        source_date=published,
    )


def quarter_bounds(label: str) -> tuple[date, date]:
    year_text, quarter_text = label.split("Q")
    year = int(year_text)
    quarter = int(quarter_text)
    start_template, end_template = QUARTER_BOUNDS[quarter]
    return (
        date(year, start_template.month, start_template.day),
        date(year, end_template.month, end_template.day),
    )


def _shares_fact(company: Company, source: Source, rows: list[dict], code: str) -> FinancialFact | None:
    row = next((item for item in rows if str(item.get("公司代號")) == code), None)
    if row is None:
        return None
    raw = row.get("已發行普通股數或TDR原股發行股數")
    if raw in (None, ""):
        return None
    published = _roc_date(str(row.get("出表日期") or ""))
    return _make_fact(
        company=company,
        metric="shares_outstanding",
        value=Decimal(str(raw)),
        unit="shares",
        currency=None,
        period_type=PeriodType.point_in_time,
        definition=(
            "Issued common shares from the Taiwan exchange company profile. "
            "This is the home-market share count, not a US stand-in share."
        ),
        source=source,
        claim_type=ClaimType.reported,
        as_of=published,
        concept="issued_common_shares",
        source_date=published,
    )


def _roc_date(value: str) -> date:
    """Taiwan file dates use a year count that starts at 1912. 1151031 is 31 Oct 2026."""
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) < 7:
        return date.today()
    year = int(digits[:3]) + 1911
    month = int(digits[3:5])
    day = int(digits[5:7])
    return date(year, month, day)


def _append_identity_facts(company: Company, facts: list[FinancialFact], source: Source) -> None:
    latest = max(
        (fact.period_end_date or fact.as_of_date for fact in facts if fact.period_end_date or fact.as_of_date),
        default=date.today(),
    )
    facts.append(
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
            as_of=latest,
        )
    )
    facts.append(
        _make_fact(
            company=company,
            metric="fiscal_period",
            value=Decimal(str(latest.toordinal())),
            unit="date_ordinal",
            currency=None,
            period_type=PeriodType.point_in_time,
            definition=f"Latest home-market period end {latest.isoformat()}",
            source=source,
            claim_type=ClaimType.reported,
            as_of=latest,
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
            definition=f"Valuation listing {company.listing} on {company.exchange}.",
            source=source,
            claim_type=ClaimType.reported,
            as_of=latest,
        )
    )
