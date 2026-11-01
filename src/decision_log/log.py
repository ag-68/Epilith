from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from data.hashing import content_hash
from research.models import Assumption, ResearchRun

UserActionKind = Literal["bought", "skipped", "watched"]


class DecisionEntry(BaseModel):
    """One research conclusion as it stood when written. Never edited afterwards."""

    model_config = ConfigDict(extra="forbid")

    entry_id: str
    timestamp: datetime
    ticker: str
    listing: str
    price: Decimal | None
    price_as_of: datetime | None
    data_snapshot_id: str
    source_bundle_id: str
    research_run_id: str
    model: str
    model_version: str | None
    red_team_model: str
    red_team_model_version: str | None
    prompt_version: str
    memo_path: str
    memo_hash: str
    red_team_path: str
    red_team_hash: str
    assumptions: list[Assumption]
    invalidation_conditions: list[str]
    conclusion: str
    conclusion_conditions: list[str]
    notes: list[str] = Field(default_factory=list)


class UserAction(BaseModel):
    """What the person did with an entry. Appended beside it, never written into it."""

    model_config = ConfigDict(extra="forbid")

    entry_id: str
    recorded_at: datetime
    user_action: UserActionKind
    user_action_reason: str
    override_notes: str | None = None


class DecisionLog:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.entries_dir = root / "entries"
        self.actions_dir = root / "actions"
        self.entries_dir.mkdir(parents=True, exist_ok=True)
        self.actions_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = root / "index.jsonl"

    def append(self, run: ResearchRun) -> DecisionEntry:
        artifact_dir = Path(run.artifact_dir)
        red_team_path = artifact_dir / "red_team.json"
        analyst = next((m for m in run.model_runs if m.purpose == "analyst"), None)
        red_team = next((m for m in run.model_runs if m.purpose == "red_team"), None)
        timestamp = datetime.now(timezone.utc)
        entry = DecisionEntry(
            entry_id=f"{timestamp.strftime('%Y%m%dT%H%M%SZ')}_{run.ticker}_{run.memo_hash[:8]}",
            timestamp=timestamp,
            ticker=run.ticker,
            listing=run.fact_sheet.listing,
            price=run.fact_sheet.price,
            price_as_of=run.fact_sheet.price_as_of,
            data_snapshot_id=run.fact_sheet.data_snapshot_id,
            source_bundle_id=run.bundle_id,
            research_run_id=run.run_id,
            model=analyst.model if analyst else "",
            model_version=analyst.model_version if analyst else None,
            red_team_model=red_team.model if red_team else "",
            red_team_model_version=red_team.model_version if red_team else None,
            prompt_version=run.prompt_version,
            memo_path=str(artifact_dir / "memo.md"),
            memo_hash=run.memo_hash,
            red_team_path=str(red_team_path),
            red_team_hash=content_hash(red_team_path.read_bytes()) if red_team_path.exists() else "",
            assumptions=run.thesis.assumptions,
            invalidation_conditions=[a.invalidated_if for a in run.thesis.assumptions]
            + list(run.red_team.invalidation_conditions),
            conclusion=run.thesis.conclusion.label,
            conclusion_conditions=list(run.thesis.conclusion.conditions),
            notes=list(run.notes),
        )
        path = self.entries_dir / f"{entry.entry_id}.json"
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite decision log entry {path}")
        path.write_text(entry.model_dump_json(indent=2), encoding="utf-8")
        with self.index_path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "entry_id": entry.entry_id,
                        "timestamp": entry.timestamp.isoformat(),
                        "ticker": entry.ticker,
                        "conclusion": entry.conclusion,
                        "memo_hash": entry.memo_hash,
                    }
                )
                + "\n"
            )
        return entry

    def record_user_action(
        self,
        entry_id: str,
        action: UserActionKind,
        reason: str,
        override_notes: str | None = None,
    ) -> UserAction:
        if not (self.entries_dir / f"{entry_id}.json").exists():
            raise KeyError(f"No decision log entry {entry_id}")
        record = UserAction(
            entry_id=entry_id,
            recorded_at=datetime.now(timezone.utc),
            user_action=action,
            user_action_reason=reason,
            override_notes=override_notes,
        )
        sequence = len(list(self.actions_dir.glob(f"{entry_id}_*.json"))) + 1
        path = self.actions_dir / f"{entry_id}_{sequence:02d}.json"
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite user action {path}")
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        return record

    def read(self, entry_id: str) -> tuple[DecisionEntry, list[UserAction]]:
        entry = DecisionEntry.model_validate_json((self.entries_dir / f"{entry_id}.json").read_text(encoding="utf-8"))
        actions = [
            UserAction.model_validate_json(path.read_text(encoding="utf-8"))
            for path in sorted(self.actions_dir.glob(f"{entry_id}_*.json"))
        ]
        return entry, actions

    def entries(self) -> list[DecisionEntry]:
        return [
            DecisionEntry.model_validate_json(path.read_text(encoding="utf-8"))
            for path in sorted(self.entries_dir.glob("*.json"))
        ]
