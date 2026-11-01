from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from data.models import CompanyValidation


# ---------------------------------------------------------------------------
# Inputs: stored sources and validated facts
# ---------------------------------------------------------------------------

SourceKind = Literal["filing", "ir_release", "annual_report", "transcript", "news"]


class SourceExcerpt(BaseModel):
    """One stored piece of text the analyst may quote. Hashed at load time."""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    kind: SourceKind
    title: str
    url: str | None = None
    published: date | None = None
    text: str
    content_hash: str
    path: str

    @property
    def is_primary(self) -> bool:
        return self.kind != "news"


class SourceBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_id: str
    ticker: str
    excerpts: list[SourceExcerpt]
    created_at: datetime

    def by_id(self, source_id: str) -> SourceExcerpt | None:
        for excerpt in self.excerpts:
            if excerpt.source_id == source_id:
                return excerpt
        return None


class FactLine(BaseModel):
    """One validated 0a field, carried into the memo unchanged."""

    model_config = ConfigDict(extra="forbid")

    metric: str
    value: Decimal
    unit: str | None = None
    currency: str | None = None
    period_label: str | None = None
    source_id: str | None = None
    cross_check_source_id: str | None = None
    status: str


class FactSheet(BaseModel):
    """The validated facts from Experiment 0a for one company. Python owns these numbers."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    company_name: str
    listing: str
    currency: str
    data_snapshot_id: str
    report_path: str
    report_generated_at: datetime
    facts: list[FactLine]
    excluded: list[FactLine] = Field(default_factory=list)
    valuation: dict[str, str] = Field(default_factory=dict)
    valuation_notes: list[str] = Field(default_factory=list)
    price: Decimal | None = None
    price_as_of: datetime | None = None

    @classmethod
    def from_validation(
        cls,
        validation: CompanyValidation,
        *,
        company_name: str,
        listing: str,
        currency: str,
        data_snapshot_id: str,
        report_path: str,
        report_generated_at: datetime,
    ) -> FactSheet:
        facts: list[FactLine] = []
        excluded: list[FactLine] = []
        for field in validation.fields:
            if field.value is None:
                continue
            line = FactLine(
                metric=field.metric,
                value=field.value,
                unit=field.unit,
                currency=field.currency,
                period_label=field.period_label,
                source_id=field.source_id,
                cross_check_source_id=field.cross_check_source_id,
                status=field.status.value,
            )
            (facts if field.status.value == "valid" else excluded).append(line)
        valuation: dict[str, str] = {}
        notes: list[str] = []
        price = None
        price_as_of = None
        if validation.valuation:
            panel = validation.valuation
            price = panel.price
            price_as_of = panel.price_as_of
            notes = list(panel.notes)
            for key in (
                "market_cap",
                "enterprise_value",
                "trailing_pe",
                "ev_sales",
                "fcf",
                "fcf_yield",
                "ttm_end_date",
                "balance_sheet_as_of",
            ):
                value = getattr(panel, key)
                if value is not None:
                    valuation[key] = format(value, "f") if isinstance(value, Decimal) else str(value)
        return cls(
            ticker=validation.ticker,
            company_name=company_name,
            listing=listing,
            currency=currency,
            data_snapshot_id=data_snapshot_id,
            report_path=report_path,
            report_generated_at=report_generated_at,
            facts=facts,
            excluded=excluded,
            valuation=valuation,
            valuation_notes=notes,
            price=price,
            price_as_of=price_as_of,
        )


# ---------------------------------------------------------------------------
# LLM outputs. No defaults: strict schema requires every field.
# ---------------------------------------------------------------------------


class ClaimDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str
    exact_quote: str
    source_id: str


class EvidenceDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claims: list[ClaimDraft]


class Assumption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    value: str
    rationale: str
    evidence_ids: list[str]
    invalidated_if: str


class RiskItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    description: str
    evidence_ids: list[str]


class LikelyWrong(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assumption_id: str
    why: str


class VerificationStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str
    method: str


class Conclusion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: Literal["Candidate", "Watch", "Avoid"]
    conditions: list[str]
    reasoning: str


class Thesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business: str
    ai_infrastructure_exposure: str
    financial_interpretation: str
    bull_thesis: list[str]
    bear_thesis: list[str]
    key_risks: list[RiskItem]
    valuation_interpretation: str
    assumptions: list[Assumption]
    most_likely_wrong: list[LikelyWrong]
    how_to_verify: list[VerificationStep]
    conclusion: Conclusion


class Attack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: str
    argument: str
    evidence_ids: list[str]


class Contradiction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    contradicts: str


class RedTeamOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attacks: list[Attack]
    contradictory_evidence: list[Contradiction]
    missing_risks: list[str]
    alternative_explanations: list[str]
    invalidation_conditions: list[str]
    overall_assessment: str


# ---------------------------------------------------------------------------
# Verified artifacts produced by Python
# ---------------------------------------------------------------------------


class EvidenceClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    claim: str
    exact_quote: str
    source_id: str
    verified: bool
    note: str | None = None


class EvidenceSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claims: list[EvidenceClaim]

    @property
    def verified(self) -> list[EvidenceClaim]:
        return [claim for claim in self.claims if claim.verified]

    @property
    def unverified(self) -> list[EvidenceClaim]:
        return [claim for claim in self.claims if not claim.verified]


class NumberFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: str
    token: str
    context: str


class ModelRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purpose: str
    provider: str
    model: str
    model_version: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class ResearchRun(BaseModel):
    """Everything one 0b run produced, referenced by the decision log."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    ticker: str
    created_at: datetime
    prompt_version: str
    fact_sheet: FactSheet
    bundle_id: str
    evidence: EvidenceSet
    thesis: Thesis
    red_team: RedTeamOutput
    number_findings: list[NumberFinding]
    model_runs: list[ModelRun]
    notes: list[str] = Field(default_factory=list)
    memo_markdown: str
    memo_hash: str
    artifact_dir: str
