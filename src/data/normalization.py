from __future__ import annotations

from typing import Any

from data.models import FinancialSnapshot


def snapshot_to_normalized(snapshot: FinancialSnapshot) -> dict[str, Any]:
    return snapshot.model_dump(mode="json")
