from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from data.hashing import content_hash
from llm.base import ChatMessage, LLMProvider, LLMRequest, LLMResponse
from llm.config import LLMConfig
from llm.recorder import LLMCallStore
from llm.schema import strict_schema
from research.evidence import verify_claims
from research.memo import render_memo
from research.models import (
    EvidenceDraft,
    EvidenceSet,
    FactSheet,
    ModelRun,
    RedTeamOutput,
    ResearchRun,
    SourceBundle,
    Thesis,
)
from research.numbers import audit_numbers
from research.prompts import (
    ANALYST_SYSTEM,
    EVIDENCE_SYSTEM,
    PROMPT_VERSION,
    RED_TEAM_SYSTEM,
    analyst_user,
    evidence_user,
    red_team_user,
)

T = TypeVar("T", bound=BaseModel)

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def parse_reply(content: str, model: type[T]) -> T:
    text = _FENCE.sub("", content.strip())
    try:
        return model.model_validate_json(text)
    except ValidationError as exc:
        raise ValueError(f"Model reply did not match {model.__name__}: {exc.errors()[:3]}\nReply head: {text[:300]}") from exc


class ResearchPipeline:
    """Validated facts + stored sources -> evidence -> thesis -> red team -> memo.

    The analyst step receives only ``FactSheet``, ``EvidenceSet`` and ``SourceBundle``.
    There is no parameter for portfolio, desired outcome, or sector preference, by design.
    """

    def __init__(
        self,
        provider: LLMProvider,
        config: LLMConfig,
        artifact_root: Path,
        *,
        prompt_version: str = PROMPT_VERSION,
    ) -> None:
        self.provider = provider
        self.config = config
        self.artifact_root = artifact_root
        self.prompt_version = prompt_version

    # -- public --------------------------------------------------------------

    def run(self, sheet: FactSheet, bundle: SourceBundle) -> ResearchRun:
        if bundle.ticker != sheet.ticker:
            raise ValueError(f"Bundle is for {bundle.ticker}, facts are for {sheet.ticker}")
        created_at = datetime.now(timezone.utc)
        run_id = f"{created_at.strftime('%Y%m%dT%H%M%SZ')}_{sheet.ticker}_{bundle.bundle_id[:8]}"
        artifact_dir = self.artifact_root / sheet.ticker / run_id
        if artifact_dir.exists():
            raise FileExistsError(f"Refusing to overwrite research run {artifact_dir}")
        artifact_dir.mkdir(parents=True)
        calls = LLMCallStore(artifact_dir / "llm_calls")
        model_runs: list[ModelRun] = []
        notes: list[str] = []

        self._write(artifact_dir / "fact_sheet.json", sheet)
        self._write(artifact_dir / "source_bundle.json", bundle)

        draft = self._ask(
            calls,
            model_runs,
            purpose="evidence",
            model=self.config.evidence_model,
            system=EVIDENCE_SYSTEM,
            user=evidence_user(bundle),
            schema=EvidenceDraft,
        )
        evidence = verify_claims(draft, bundle)
        self._write(artifact_dir / "evidence.json", evidence)
        if not evidence.verified:
            notes.append("No evidence claim passed quote verification; the thesis rests on facts alone.")

        thesis = self._ask(
            calls,
            model_runs,
            purpose="analyst",
            model=self.config.analyst_model,
            system=ANALYST_SYSTEM,
            user=analyst_user(sheet, evidence, bundle),
            schema=Thesis,
        )
        notes.extend(self._check_citations(thesis, evidence))
        self._write(artifact_dir / "thesis.json", thesis)

        red_team = self._ask(
            calls,
            model_runs,
            purpose="red_team",
            model=self.config.red_team_model,
            system=RED_TEAM_SYSTEM,
            user=red_team_user(sheet, thesis, evidence, bundle),
            schema=RedTeamOutput,
        )
        self._write(artifact_dir / "red_team.json", red_team)

        number_findings = audit_numbers(sheet, thesis, red_team)
        memo = render_memo(
            run_id=run_id,
            prompt_version=self.prompt_version,
            sheet=sheet,
            bundle=bundle,
            evidence=evidence,
            thesis=thesis,
            red_team=red_team,
            number_findings=number_findings,
            model_runs=model_runs,
        )
        (artifact_dir / "memo.md").write_text(memo, encoding="utf-8")

        result = ResearchRun(
            run_id=run_id,
            ticker=sheet.ticker,
            created_at=created_at,
            prompt_version=self.prompt_version,
            fact_sheet=sheet,
            bundle_id=bundle.bundle_id,
            evidence=evidence,
            thesis=thesis,
            red_team=red_team,
            number_findings=number_findings,
            model_runs=model_runs,
            notes=notes,
            memo_markdown=memo,
            memo_hash=content_hash(memo.encode("utf-8")),
            artifact_dir=str(artifact_dir),
        )
        self._write(artifact_dir / "run.json", result)
        return result

    # -- internals -----------------------------------------------------------

    def _ask(
        self,
        calls: LLMCallStore,
        model_runs: list[ModelRun],
        *,
        purpose: str,
        model: str,
        system: str,
        user: str,
        schema: type[T],
    ) -> T:
        request = LLMRequest(
            model=model,
            messages=[ChatMessage(role="system", content=system), ChatMessage(role="user", content=user)],
            json_schema=strict_schema(schema),
            schema_name=schema.__name__,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            purpose=purpose,
        )
        response: LLMResponse = self.provider.complete(request)
        calls.record(request, response)
        model_runs.append(
            ModelRun(
                purpose=purpose,
                provider=response.provider,
                model=response.model,
                model_version=response.model_version,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
            )
        )
        return parse_reply(response.content, schema)

    @staticmethod
    def _check_citations(thesis: Thesis, evidence: EvidenceSet) -> list[str]:
        known = {claim.evidence_id for claim in evidence.verified}
        notes: list[str] = []
        cited: set[str] = set()
        for risk in thesis.key_risks:
            cited.update(risk.evidence_ids)
        for assumption in thesis.assumptions:
            cited.update(assumption.evidence_ids)
        unknown = sorted(cited - known)
        if unknown:
            notes.append(f"Thesis cites evidence ids that are not verified: {', '.join(unknown)}")
        assumption_ids = {a.id for a in thesis.assumptions}
        missing = [item.assumption_id for item in thesis.most_likely_wrong if item.assumption_id not in assumption_ids]
        if missing:
            notes.append(f"most_likely_wrong names unknown assumptions: {', '.join(missing)}")
        if len(thesis.most_likely_wrong) != 3:
            notes.append(f"most_likely_wrong has {len(thesis.most_likely_wrong)} items; the spec asks for three")
        return notes

    @staticmethod
    def _write(path: Path, payload: BaseModel) -> None:
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite {path}")
        path.write_text(json.dumps(payload.model_dump(mode="json"), indent=2), encoding="utf-8")
