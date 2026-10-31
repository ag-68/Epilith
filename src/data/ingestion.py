from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from data.config import DATA_DIR, company_by_ticker
from data.financial_data import extract_financial_facts
from data.hashing import stable_id
from data.normalization import snapshot_to_normalized
from data.market_data import market_fact_from_quote
from data.markets import resolve_home_market
from data.models import Company, CrossCheck, DiscrepancyClass, FinancialFact, FinancialSnapshot, PeriodType, Source
from data.providers.company_report import CompanyReport, CompanyReportProvider
from data.providers.europe_esef import EuropeEsefProvider
from data.providers.google_finance import GoogleFinanceProvider
from data.providers.nasdaq import NasdaqQuoteProvider
from data.providers.sec_edgar import SecEdgarProvider
from data.providers.twse import TwseQuoteProvider
from data.providers.twse_mops import TwseMopsProvider
from data.providers.yahoo_finance import YahooFinanceProvider
from data.snapshots import SnapshotStore
from data.statement_facts import build_missing_facts
from data.statement_table import (
    StatedAmount,
    latest_independent_point,
    stated_year_total,
    sum_independent_quarters,
    ttm_candidates_from_annual_and_ytd,
)
from validation.data_quality import compare_values, home_flow_fact, source_accounting


class CompanyIngestor:
    def __init__(
        self,
        store: SnapshotStore | None = None,
        sec: SecEdgarProvider | None = None,
        nasdaq: NasdaqQuoteProvider | None = None,
        yahoo: YahooFinanceProvider | None = None,
        twse: TwseQuoteProvider | None = None,
        taiwan_filings: TwseMopsProvider | None = None,
        europe_filings: EuropeEsefProvider | None = None,
        reports: CompanyReportProvider | None = None,
        google: GoogleFinanceProvider | None = None,
    ) -> None:
        self.store = store or SnapshotStore(DATA_DIR)
        self.sec = sec or SecEdgarProvider()
        self.nasdaq = nasdaq or NasdaqQuoteProvider()
        self.yahoo = yahoo or YahooFinanceProvider()
        self.twse = twse or TwseQuoteProvider()
        self.taiwan_filings = taiwan_filings or TwseMopsProvider()
        self.europe_filings = europe_filings or EuropeEsefProvider()
        self.reports = reports or CompanyReportProvider()
        self.google = google or GoogleFinanceProvider()

    def ingest(self, ticker: str) -> tuple[FinancialSnapshot, list[CrossCheck]]:
        company = company_by_ticker(ticker)
        resolution = resolve_home_market(company)
        notes = [resolution.explanation]
        sources: list[Source] = []
        facts = []
        allow_us_exhibits = False

        if not resolution.uses_home_market_filings:
            notes.append(resolution.market.coverage.strip())
        elif resolution.market.filing_adapter == "sec_edgar":
            allow_us_exhibits = True
            xbrl_source, companyfacts = self.sec.fetch_company_facts(company, self.store)
            us_facts, us_notes = extract_financial_facts(company, companyfacts, xbrl_source)
            facts.extend(us_facts)
            notes.extend(us_notes)
            sources.append(xbrl_source)
            if xbrl_source.metadata.get("used_cached_raw"):
                notes.append(
                    "Live United States filing download failed; using a previously stored snapshot. "
                    f"Error: {xbrl_source.metadata.get('live_fetch_error')}"
                )
        elif resolution.market.filing_adapter == "twse_mops":
            tw_facts, tw_sources, tw_notes = self.taiwan_filings.fetch_financials(company, self.store)
            facts.extend(tw_facts)
            sources.extend(tw_sources)
            notes.extend(tw_notes)
        elif resolution.market.filing_adapter == "europe_esef":
            eu_facts, eu_sources, eu_notes = self.europe_filings.fetch_financials(company, self.store)
            facts.extend(eu_facts)
            sources.extend(eu_sources)
            notes.extend(eu_notes)
        else:
            notes.append(
                f"No filing adapter is wired for '{resolution.market.filing_adapter}'. "
                "The United States filing cabinet was not used."
            )

        report = self._company_report(company)
        sources.extend(report.sources)
        notes.extend(report.notes)
        filled, fill_notes = build_missing_facts(
            company,
            facts,
            report.amounts,
            {source.source_id: source for source in report.sources},
        )
        facts.extend(filled)
        notes.extend(fill_notes)

        primary, secondary = self._price_providers(resolution.market.id)
        market = None
        if primary is None:
            notes.append(f"No home-market price feed is integrated for {resolution.market.name}.")
        else:
            market_source, market_payload = primary.fetch_price(company, self.store)
            if market_payload.get("currency") and market_payload["currency"] != company.valuation_currency:
                notes.append(
                    f"Primary quote currency {market_payload.get('currency')} does not match "
                    f"valuation currency {company.valuation_currency}; listing may have been mixed."
                )
            market = market_fact_from_quote(company, market_source, market_payload)
            sources.append(market_source)

        anchor = sources[0].content_hash if sources else company.ticker
        created_at = datetime.now(timezone.utc)
        snapshot_id = stable_id(
            company.ticker,
            anchor,
            market.source_id if market else "no-price",
            created_at.isoformat(),
        )
        snapshot = FinancialSnapshot(
            snapshot_id=snapshot_id,
            company=company,
            facts=facts,
            market=market,
            sources=sources,
            created_at=created_at,
            notes=notes,
        )
        filing_source = sources[0] if sources else None
        checks = self._cross_checks(
            company,
            snapshot,
            filing_source,
            secondary,
            allow_us_exhibits=allow_us_exhibits,
            report=report,
        )
        self.store.save_normalized(
            company.ticker,
            snapshot.snapshot_id,
            snapshot_to_normalized(snapshot),
        )
        return snapshot, checks

    def _price_providers(self, market_id: str):
        if market_id == "US":
            return self.nasdaq, self.yahoo
        if market_id == "TW":
            return self.twse, self.yahoo
        if market_id == "EU":
            return self.yahoo, self.google
        return None, None

    def _cross_checks(
        self,
        company: Company,
        snapshot: FinancialSnapshot,
        filing_source: Source | None,
        secondary_market=None,
        allow_us_exhibits: bool = False,
        report: CompanyReport | None = None,
    ) -> list[CrossCheck]:
        checks: list[CrossCheck] = []

        if secondary_market is None:
            checks.append(
                CrossCheck(
                    metric="price",
                    primary_value=snapshot.market.price if snapshot.market else None,
                    primary_source_id=snapshot.market.source_id if snapshot.market else None,
                    classification=DiscrepancyClass.unresolved,
                    explanation=(
                        "No second, independent price source for this listing yet. "
                        "A second copy of the same website does not count."
                    ),
                    passed=False,
                )
            )
        else:
            try:
                other_source, other_payload = secondary_market.fetch_price(company, self.store)
                snapshot.sources.append(other_source)
                other_price = Decimal(str(other_payload["price"]))
                if snapshot.market:
                    if other_payload.get("currency") and other_payload["currency"] != snapshot.market.currency:
                        checks.append(
                            CrossCheck(
                                metric="price",
                                primary_value=snapshot.market.price,
                                primary_source_id=snapshot.market.source_id,
                                cross_check_value=other_price,
                                cross_check_source_id=other_source.source_id,
                                classification=DiscrepancyClass.currency,
                                explanation=(
                                    f"Primary quote currency {snapshot.market.currency} vs "
                                    f"{other_payload.get('currency')}"
                                ),
                                passed=False,
                            )
                        )
                    else:
                        checks.append(
                            compare_values(
                                "price",
                                snapshot.market.price,
                                snapshot.market.source_id,
                                other_price,
                                other_source.source_id,
                                "Price differs by more than 1% across providers without a documented listing/timing explanation.",
                                DiscrepancyClass.timing,
                            )
                        )
            except Exception as exc:
                checks.append(
                    CrossCheck(
                        metric="price",
                        primary_value=snapshot.market.price if snapshot.market else None,
                        primary_source_id=snapshot.market.source_id if snapshot.market else None,
                        classification=DiscrepancyClass.unresolved,
                        explanation=f"Second price source failed: {exc}",
                        passed=False,
                    )
                )

        amounts = list(report.amounts if report else [])
        amounts.extend(_home_annual_amounts(snapshot))
        origins = {source.source_id: source.origin for source in snapshot.sources}
        for metric in ("revenue", "net_income", "operating_cash_flow", "capex"):
            official = home_flow_fact(snapshot, metric)
            if official is not None and official.period_type is PeriodType.annual:
                checks.append(_check_home_year(snapshot, amounts, metric, official, report))
                continue
            ttm = snapshot.latest_fact(metric, PeriodType.ttm)
            primary_ids = {
                fact.source_id
                for fact in snapshot.facts_for(metric)
                if fact.period_type in {PeriodType.ttm, PeriodType.quarterly}
            }
            style = _statement_style(company, report, ttm.source_id if ttm else None)
            same_style = [item for item in amounts if item.accounting == style]
            summed = sum_independent_quarters(
                same_style,
                metric,
                primary_ids,
                end_on=ttm.period_end_date if ttm else None,
            )
            if ttm and summed:
                other, other_source, _start, other_end = summed
                if ttm.period_end_date and abs((ttm.period_end_date - other_end).days) > 5:
                    checks.append(
                        CrossCheck(
                            metric=metric,
                            primary_value=ttm.value,
                            primary_source_id=ttm.source_id,
                            cross_check_value=other,
                            cross_check_source_id=other_source,
                            classification=DiscrepancyClass.period,
                            explanation=(
                                f"The company report's last four quarters end on {other_end.isoformat()}, "
                                f"while the first source ends on {ttm.period_end_date.isoformat()}."
                            ),
                            passed=False,
                        )
                    )
                else:
                    checks.append(
                        compare_values(
                            metric,
                            ttm.value,
                            ttm.source_id,
                            other,
                            other_source,
                            "The sum of the last four quarters in the company report differs by more than 1%.",
                            DiscrepancyClass.unresolved,
                        )
                    )
            else:
                rebuilt = None
                if ttm and ttm.period_end_date and ttm.value:
                    rebuilt = _pick_rebuild(
                        ttm.value,
                        ttm_candidates_from_annual_and_ytd(same_style, metric, primary_ids, ttm.period_end_date),
                        origins,
                    )
                if ttm and rebuilt:
                    other, other_source = rebuilt
                    checks.append(
                        compare_values(
                            metric,
                            ttm.value,
                            ttm.source_id,
                            other,
                            other_source,
                            "The other report's full year, plus this year-to-date, minus last year's year-to-date, differs by more than 1%.",
                            DiscrepancyClass.accounting_definition,
                        )
                    )
                else:
                    separate = _note_separate_indicator(snapshot, amounts, metric, style)
                    quarter_rows = [item for item in amounts if item.metric == metric and item.kind == "quarter"]
                    same_document = bool(quarter_rows) and all(item.source_id in primary_ids for item in quarter_rows)
                    if separate:
                        explanation = (
                            "No other document states this same twelve-month total. "
                            "The home-market yearly report is a separate indicator and was not used as confirmation."
                        )
                    elif same_document:
                        explanation = (
                            "The company report is already the source of these quarters. "
                            "No other document states the same twelve-month total in the same accounting rules."
                        )
                    else:
                        explanation = (
                            "The second document does not contain four quarters of its own for this line, "
                            "and a full-year rebuild was not available. Quarters from the first source were not reused."
                        )
                    checks.append(
                        CrossCheck(
                            metric=metric,
                            primary_value=ttm.value if ttm else None,
                            primary_source_id=ttm.source_id if ttm else (filing_source.source_id if filing_source else None),
                            classification=DiscrepancyClass.unresolved,
                            explanation=explanation,
                            passed=False,
                        )
                    )

        headlines = report.headlines if report else {}
        headline_source = report.headline_source_id if report else None
        for metric in ("total_debt", "cash", "shares_outstanding"):
            fact = snapshot.latest_fact(metric)
            primary_ids = {fact.source_id} if fact else set()
            point_metric = metric
            fact_style = _statement_style(company, report, fact.source_id if fact else None)
            report_style = _statement_style(company, report, headline_source)
            point_amounts = list(amounts)
            if metric == "total_debt":
                point_amounts = [item for item in point_amounts if item.priority >= 2]
            point = latest_independent_point(
                point_amounts,
                point_metric,
                primary_ids,
                as_of=fact.as_of_date if fact else None,
            )
            headline = (
                headlines.get(metric)
                if headline_source and headline_source not in primary_ids and report_style == fact_style
                else None
            )
            if fact and point:
                checks.append(
                    compare_values(
                        metric,
                        fact.value,
                        fact.source_id,
                        point[0],
                        point[1],
                        f"The company report's {metric.replace('_', ' ')} differs by more than 1%.",
                        DiscrepancyClass.accounting_definition,
                    )
                )
            elif fact and headline:
                checks.append(
                    compare_values(
                        metric,
                        fact.value,
                        fact.source_id,
                        headline["value"],
                        headline_source or "company_report",
                        f"The company report's {metric.replace('_', ' ')} differs by more than 1%.",
                        DiscrepancyClass.accounting_definition,
                    )
                )
            else:
                implied = (
                    _shares_from_capital(amounts, primary_ids, snapshot)
                    if metric == "shares_outstanding" and fact is not None and fact.value
                    else None
                )
                if implied is not None:
                    other, other_source, capital_end = implied
                    checks.append(
                        compare_values(
                            metric,
                            fact.value,
                            fact.source_id,
                            other,
                            other_source,
                            "The company's capital stock divided by the exchange's printed face amount differs from the issued share count by more than 1%.",
                            DiscrepancyClass.accounting_definition,
                        )
                    )
                    snapshot.notes.append(
                        "The share count was checked against the company's capital stock "
                        f"dated {capital_end.isoformat()}, divided by the face amount printed on the exchange profile "
                        f"dated {fact.as_of_date.isoformat() if fact.as_of_date else 'an unknown day'}."
                    )
                    continue
                component = _matching_long_term_debt(snapshot, amounts) if metric == "total_debt" else None
                if component is not None and fact is not None:
                    company_long, current_portion = component
                    checks.append(
                        CrossCheck(
                            metric=metric,
                            primary_value=fact.value,
                            primary_source_id=fact.source_id,
                            cross_check_value=company_long.value,
                            cross_check_source_id=company_long.source_id,
                            difference=fact.value - company_long.value,
                            classification=DiscrepancyClass.accounting_definition,
                            explanation=(
                                f"Long-term borrowings of {company_long.value} on {company_long.end.isoformat()} match the company report. "
                                f"The portion due within a year, {current_portion.value}, is only in the home-market report. "
                                "The total kept is the home-market total."
                            ),
                            passed=True,
                        )
                    )
                elif metric == "total_debt" and _incomplete_debt(amounts, primary_ids, fact_style):
                    checks.append(
                        CrossCheck(
                            metric=metric,
                            primary_value=fact.value if fact else None,
                            primary_source_id=fact.source_id if fact else (filing_source.source_id if filing_source else None),
                            classification=DiscrepancyClass.accounting_definition,
                            explanation=(
                                "The other report does not list both the short-term and the long-term portions, "
                                "so it does not state the same borrowings total."
                            ),
                            passed=False,
                        )
                    )
                else:
                    checks.append(_missing_second_document(metric, fact, filing_source))
        _note_later_balance_sheet(snapshot, amounts)
        _note_earlier_agreement(snapshot, amounts, "cash", "cash")
        _note_earlier_agreement(snapshot, amounts, "total_debt", "borrowings")
        if allow_us_exhibits and report and not report.amounts and not report.headlines:
            snapshot.notes.append("The United States earnings-release file was not used to fill missing company-report quarters.")
        return checks

    def _company_report(self, company: Company) -> CompanyReport:
        try:
            return self.reports.fetch(company, self.store)
        except Exception as exc:
            return CompanyReport(notes=[f"Company report step failed: {exc}"])


def _home_annual_amounts(snapshot: FinancialSnapshot) -> list[StatedAmount]:
    origins = {source.source_id: source.origin for source in snapshot.sources}
    found: list[StatedAmount] = []
    for fact in snapshot.facts:
        origin = origins.get(fact.source_id)
        if origin == "europe_esef" and fact.period_type is PeriodType.annual and fact.period_start_date and fact.period_end_date:
            found.append(
                StatedAmount(
                    metric=fact.metric,
                    kind="annual",
                    start=fact.period_start_date,
                    end=fact.period_end_date,
                    value=fact.value,
                    source_id=fact.source_id,
                    priority=2,
                    accounting=snapshot.company.accounting,
                )
            )
        elif (
            origins.get(fact.source_id) in {"europe_esef", "twse_mops"}
            and fact.period_type is PeriodType.point_in_time
            and fact.as_of_date
            and fact.metric in {"cash", "total_debt", "shares_outstanding"}
        ):
            found.append(
                StatedAmount(
                    metric=fact.metric,
                    kind="instant",
                    start=None,
                    end=fact.as_of_date,
                    value=fact.value,
                    source_id=fact.source_id,
                    priority=2,
                    accounting=snapshot.company.accounting,
                )
            )
    return found


def _pick_rebuild(
    primary: Decimal,
    candidates: list[tuple[Decimal, str]],
    origins: dict[str, str],
) -> tuple[Decimal, str] | None:
    within: list[tuple[Decimal, str]] = []
    for value, source_id in candidates:
        if primary == 0:
            continue
        if abs(primary - value) / abs(primary) <= Decimal("0.01"):
            within.append((value, source_id))
    if not within:
        return None
    within.sort(key=lambda item: (origins.get(item[1]) == "sec_edgar", abs(primary - item[0])))
    return within[0]


def _check_home_year(
    snapshot: FinancialSnapshot,
    amounts: list[StatedAmount],
    metric: str,
    official: FinancialFact,
    report: CompanyReport | None,
) -> CrossCheck:
    """Compare the home-market full year with the company report's same year."""
    if official.period_start_date is None or official.period_end_date is None or not official.value:
        return _missing_second_document(metric, official, None)
    report_ids = {source.source_id for source in report.sources} if report else set()
    company_rows = [item for item in amounts if item.source_id in report_ids] if report_ids else amounts
    found = stated_year_total(company_rows, metric, official.period_start_date, official.period_end_date)
    if found is None:
        return CrossCheck(
            metric=metric,
            primary_value=official.value,
            primary_source_id=official.source_id,
            classification=DiscrepancyClass.unresolved,
            explanation="The company report does not state this same year, so the home-market year has no second reading.",
            passed=False,
        )
    other, other_source = found
    other_rules = source_accounting(snapshot, other_source)
    home_rules = source_accounting(snapshot, official.source_id)
    gap = abs(official.value - other) / abs(official.value)
    if gap <= Decimal("0.01"):
        return compare_values(
            metric,
            official.value,
            official.source_id,
            other,
            other_source,
            "The company report's figure for the same year differs by more than 1%.",
            DiscrepancyClass.unresolved,
        )
    if other_rules != home_rules:
        snapshot.notes.append(
            f"{metric.replace('_', ' ')} for the year ended {official.period_end_date.isoformat()} "
            f"is {official.value} under the home market's accounting rules. "
            f"The company report states {other} for that same year under its own rules. "
            "The home-market figure is the one kept."
        )
        return CrossCheck(
            metric=metric,
            primary_value=official.value,
            primary_source_id=official.source_id,
            cross_check_value=other,
            cross_check_source_id=other_source,
            difference=official.value - other,
            difference_pct=gap,
            classification=DiscrepancyClass.accounting_definition,
            explanation=(
                f"Same year, different accounting rules. The home-market figure {official.value} is the one kept. "
                f"The company report states {other}."
            ),
            passed=True,
        )
    return compare_values(
        metric,
        official.value,
        official.source_id,
        other,
        other_source,
        "The company report's figure for the same year differs by more than 1%.",
        DiscrepancyClass.unresolved,
    )


def _matching_long_term_debt(
    snapshot: FinancialSnapshot,
    amounts: list[StatedAmount],
) -> tuple[StatedAmount, FinancialFact] | None:
    long_term = snapshot.latest_fact("debt_noncurrent")
    current = snapshot.latest_fact("debt_current")
    if long_term is None or current is None or long_term.as_of_date is None or not long_term.value:
        return None
    if long_term.as_of_date != current.as_of_date:
        return None
    rows = [
        item
        for item in amounts
        if item.metric == "debt_noncurrent"
        and item.source_id != long_term.source_id
        and abs((item.end - long_term.as_of_date).days) <= 5
    ]
    if not rows:
        return None
    other = max(rows, key=lambda item: item.priority)
    if abs(long_term.value - other.value) / abs(long_term.value) > Decimal("0.01"):
        return None
    return other, current


def _shares_from_capital(
    amounts: list[StatedAmount],
    primary_ids: set[str],
    snapshot: FinancialSnapshot,
) -> tuple[Decimal, str, date] | None:
    par = snapshot.latest_fact("par_value")
    if par is None or not par.value:
        return None
    capitals = [
        item
        for item in amounts
        if item.metric == "capital_stock" and item.kind == "instant" and item.source_id not in primary_ids
    ]
    if not capitals:
        return None
    capital = max(capitals, key=lambda item: item.end)
    return capital.value / par.value, capital.source_id, capital.end


def _statement_style(company: Company, report: CompanyReport | None, source_id: str | None) -> str:
    if report and source_id and any(source.source_id == source_id for source in report.sources):
        return report.statement_language or company.accounting
    return company.accounting


def _note_separate_indicator(
    snapshot: FinancialSnapshot,
    amounts: list[StatedAmount],
    metric: str,
    style: str,
) -> bool:
    annuals = [
        item
        for item in amounts
        if item.metric == metric and item.kind == "annual" and item.accounting and item.accounting != style
    ]
    if not annuals:
        return False
    annual = max(annuals, key=lambda item: item.end)
    snapshot.notes.append(
        f"The home-market yearly report states {metric.replace('_', ' ')} of {annual.value} "
        f"for the year ended {annual.end.isoformat()} under its own accounting rules. "
        "The twelve-month total uses a different set of rules, so this yearly figure is a separate indicator "
        "and is not a confirmation."
    )
    return True


def _incomplete_debt(amounts: list[StatedAmount], primary_ids: set[str], style: str) -> bool:
    others = [
        item
        for item in amounts
        if item.metric == "total_debt"
        and item.kind == "instant"
        and item.source_id not in primary_ids
        and item.accounting == style
    ]
    return bool(others) and all(item.priority < 2 for item in others)


def _missing_second_document(metric: str, fact: FinancialFact | None, filing_source: Source | None) -> CrossCheck:
    return CrossCheck(
        metric=metric,
        primary_value=fact.value if fact else None,
        primary_source_id=fact.source_id if fact else (filing_source.source_id if filing_source else None),
        classification=DiscrepancyClass.unresolved,
        explanation="No second document states this line. The first source was not compared with itself.",
        passed=False,
    )


def _note_later_balance_sheet(snapshot: FinancialSnapshot, amounts: list[StatedAmount]) -> None:
    for metric, label in (("cash", "cash"), ("total_debt", "borrowings")):
        fact = snapshot.latest_fact(metric)
        if fact is None or fact.as_of_date is None:
            continue
        later = [
            item
            for item in amounts
            if item.metric == metric and item.kind == "instant" and item.end > fact.as_of_date and (item.end - fact.as_of_date).days > 5
        ]
        if not later:
            continue
        newest = max(later, key=lambda item: item.end)
        same_day = [
            item
            for item in amounts
            if item.metric == metric
            and item.kind == "instant"
            and item.source_id != fact.source_id
            and abs((item.end - fact.as_of_date).days) <= 5
            and fact.value
            and abs(item.value - fact.value) / abs(fact.value) <= Decimal("0.01")
        ]
        confirmed = (
            f" The confirmed {label} is the {fact.as_of_date.isoformat()} figure both documents state."
            if same_day
            else ""
        )
        snapshot.notes.append(
            f"A later statement shows {label} of {newest.value} on {newest.end.isoformat()}. "
            f"No second document states that later figure.{confirmed}"
        )


def _note_earlier_agreement(
    snapshot: FinancialSnapshot,
    amounts: list[StatedAmount],
    metric: str,
    label: str,
) -> None:
    fact = snapshot.latest_fact(metric)
    if fact is None or fact.as_of_date is None:
        return
    origins = {source.source_id: source.origin for source in snapshot.sources}
    if _paired_on(amounts, metric, fact.as_of_date, origins, fact.source_id):
        return
    older = [
        item
        for item in amounts
        if item.metric == metric and item.kind == "instant" and (fact.as_of_date - item.end).days > 5
    ]
    by_end: dict[date, list[StatedAmount]] = {}
    for item in older:
        by_end.setdefault(item.end, []).append(item)
    for end in sorted(by_end, reverse=True):
        paired = _paired_rows(by_end[end], origins)
        if paired is None:
            continue
        snapshot.notes.append(
            f"On {end.isoformat()}, the company report and the home-market filing both state {label} of {paired}. "
            f"The latest figure, on {fact.as_of_date.isoformat()}, does not have a second document."
        )
        return


def _paired_on(
    amounts: list[StatedAmount],
    metric: str,
    as_of: date,
    origins: dict[str, str],
    primary_source_id: str,
) -> bool:
    near = [
        item
        for item in amounts
        if item.metric == metric
        and item.kind == "instant"
        and item.source_id != primary_source_id
        and abs((item.end - as_of).days) <= 5
    ]
    return _paired_rows(near, origins) is not None


def _paired_rows(rows: list[StatedAmount], origins: dict[str, str]) -> Decimal | None:
    by_origin: dict[str, StatedAmount] = {}
    for item in rows:
        by_origin.setdefault(origins.get(item.source_id, item.source_id), item)
    chosen = list(by_origin.values())
    if len(chosen) < 2 or chosen[0].value == 0:
        return None
    if abs(chosen[0].value - chosen[1].value) / abs(chosen[0].value) > Decimal("0.01"):
        return None
    return chosen[0].value
