from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ClaimType(str, Enum):
    reported = "reported"
    computed = "computed"
    consensus = "consensus"
    inference = "inference"
    speculation = "speculation"


class PeriodType(str, Enum):
    annual = "annual"
    quarterly = "quarterly"
    ttm = "TTM"
    point_in_time = "point_in_time"


class DiscrepancyClass(str, Enum):
    currency = "currency"
    unit = "unit"
    period = "period"
    listing_adr = "listing/ADR"
    accounting_definition = "accounting-definition"
    timing = "timing"
    source_error = "source error"
    unresolved = "unresolved"


class FieldStatus(str, Enum):
    valid = "valid"
    failed = "failed"
    missing = "missing"


class Company(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str
    name: str
    cik: str
    region: str
    accounting: str
    reporting_currency: str
    listing: str
    exchange: str
    valuation_currency: str
    yahoo_symbol: str
    stooq_symbol: str
    google_symbol: str = ""
    market_id: str = "US"
    local_code: str = ""
    ir_release_urls: list[str] = []
    enabled_for_exp0a: bool = False


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    origin: str
    name: str
    url: str | None = None
    retrieved_at: datetime
    content_hash: str
    raw_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FinancialFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_id: str
    metric: str
    value: Decimal
    unit: str
    currency: str | None = None
    period_type: PeriodType
    period_start_date: date | None = None
    period_end_date: date | None = None
    as_of_date: date | None = None
    listing: str | None = None
    definition: str
    source_id: str
    source_date: date | None = None
    retrieved_at: datetime
    content_hash: str
    claim_type: ClaimType
    formula: str | None = None
    input_fact_ids: list[str] = Field(default_factory=list)
    concept: str | None = None
    accession: str | None = None

    @model_validator(mode="after")
    def check_period_fields(self) -> FinancialFact:
        if self.period_type in {PeriodType.quarterly, PeriodType.annual, PeriodType.ttm}:
            if self.period_start_date is None or self.period_end_date is None:
                raise ValueError(f"{self.period_type} facts require period start and end dates")
        if self.period_type is PeriodType.point_in_time and self.as_of_date is None:
            raise ValueError("point_in_time facts require as_of_date")
        if self.claim_type is ClaimType.computed and not self.formula:
            raise ValueError("computed facts require a formula")
        return self


class MarketFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_id: str
    price: Decimal
    currency: str
    listing: str
    as_of_timestamp: datetime
    market_status: str
    source_id: str
    retrieved_at: datetime
    content_hash: str
    definition: str = "Last available trade/quote for the primary listing. Not called current unless the timestamp and market status are known."


class FinancialSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: str
    company: Company
    facts: list[FinancialFact]
    market: MarketFact | None = None
    sources: list[Source] = Field(default_factory=list)
    created_at: datetime
    notes: list[str] = Field(default_factory=list)

    def facts_for(self, metric: str, period_type: PeriodType | None = None) -> list[FinancialFact]:
        out = [f for f in self.facts if f.metric == metric]
        if period_type is not None:
            out = [f for f in out if f.period_type == period_type]
        return out

    def latest_fact(self, metric: str, period_type: PeriodType | None = None) -> FinancialFact | None:
        facts = self.facts_for(metric, period_type)
        if not facts:
            return None

        def sort_key(fact: FinancialFact) -> date:
            return fact.period_end_date or fact.as_of_date or date.min

        return max(facts, key=sort_key)


class ValuationPanel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    listing: str
    currency: str
    market_cap: Decimal | None = None
    enterprise_value: Decimal | None = None
    trailing_pe: Decimal | None = None
    ev_sales: Decimal | None = None
    fcf: Decimal | None = None
    fcf_yield: Decimal | None = None
    price: Decimal | None = None
    shares_outstanding: Decimal | None = None
    total_debt: Decimal | None = None
    cash: Decimal | None = None
    ttm_revenue: Decimal | None = None
    ttm_net_income: Decimal | None = None
    ttm_operating_cash_flow: Decimal | None = None
    ttm_capex: Decimal | None = None
    price_as_of: datetime | None = None
    ttm_end_date: date | None = None
    balance_sheet_as_of: date | None = None
    notes: list[str] = Field(default_factory=list)


class CrossCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str
    primary_value: Decimal | None = None
    primary_source_id: str | None = None
    cross_check_value: Decimal | None = None
    cross_check_source_id: str | None = None
    difference: Decimal | None = None
    difference_pct: Decimal | None = None
    classification: DiscrepancyClass | None = None
    explanation: str | None = None
    passed: bool = False


class FieldResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str
    value: Decimal | None = None
    unit: str | None = None
    currency: str | None = None
    period_label: str | None = None
    source_id: str | None = None
    cross_check_source_id: str | None = None
    cross_check_value: Decimal | None = None
    difference: Decimal | None = None
    status: FieldStatus
    notes: list[str] = Field(default_factory=list)


class CompanyValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str
    valid_count: int
    required_count: int = 12
    fields: list[FieldResult]
    discrepancies: list[CrossCheck] = Field(default_factory=list)
    valuation: ValuationPanel | None = None
    findings: list[str] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.valid_count >= 11


class ExperimentReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment: Literal["0a"] = "0a"
    generated_at: datetime
    companies: list[CompanyValidation]
    overall_passed: bool
    findings: list[str] = Field(default_factory=list)
