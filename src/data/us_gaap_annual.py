"""Read a stored US-accounting annual report. Does not download one.

Ingestion does not call this. A US-rules annual report is a different
indicator from a home-market report that uses other accounting rules, so it
is not a confirmation of that home-market figure.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from data.models import Source
from data.snapshots import SnapshotStore
from data.statement_table import StatedAmount

_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A"}
_FLOWS = {
    "revenue": (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ),
    "net_income": ("NetIncomeLoss",),
    "operating_income": ("OperatingIncomeLoss",),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
    "capex": (
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ),
}


def stored_us_gaap_annual(
    store: SnapshotStore, ticker: str, currency: str
) -> tuple[list[StatedAmount], Source | None]:
    source = store.latest_raw("sec_edgar", ticker, "companyfacts.json")
    if source is None or not source.raw_path:
        return [], None
    payload = json.loads(Path(source.raw_path).read_text(encoding="utf-8"))
    facts = payload.get("facts") or {}
    us = facts.get("us-gaap") or {}
    amounts: list[StatedAmount] = []
    for metric, concepts in _FLOWS.items():
        row = _latest_fy(us, concepts, currency)
        if row is None:
            continue
        end = date.fromisoformat(row["end"])
        amounts.append(
            StatedAmount(
                metric=metric,
                kind="annual",
                start=date(end.year, 1, 1),
                end=end,
                value=Decimal(str(row["val"])),
                source_id=source.source_id,
                priority=2,
            )
        )
    cash = _latest_fy(us, ("CashAndCashEquivalentsAtCarryingValue",), currency)
    if cash is not None:
        amounts.append(
            _instant("cash", cash, source.source_id, priority=2)
        )
    current = _latest_fy(us, ("LongTermDebtCurrent",), currency)
    noncurrent = _latest_fy(us, ("LongTermDebtNoncurrent",), currency)
    if current is not None and noncurrent is not None and current["end"] == noncurrent["end"]:
        combined = dict(current)
        combined["val"] = Decimal(str(current["val"])) + Decimal(str(noncurrent["val"]))
        amounts.append(_instant("total_debt", combined, source.source_id, priority=2))
    shares = _latest_share_count(facts.get("dei") or {})
    if shares is not None:
        amounts.append(_instant("shares_outstanding", shares, source.source_id, priority=2))
    return amounts, source


def _latest_fy(us: dict, concepts: tuple[str, ...], currency: str) -> dict | None:
    chosen: dict | None = None
    for concept in concepts:
        node = us.get(concept) or {}
        for unit, items in (node.get("units") or {}).items():
            if str(unit).lower() != currency.lower():
                continue
            for item in items:
                if item.get("fp") != "FY" or item.get("form") not in _FORMS:
                    continue
                if item.get("val") in (None, ""):
                    continue
                if chosen is None or str(item.get("end")) > str(chosen.get("end")):
                    chosen = item
                elif str(item.get("end")) == str(chosen.get("end")) and str(item.get("filed", "")) > str(
                    chosen.get("filed", "")
                ):
                    chosen = item
    return chosen


def _latest_share_count(dei: dict) -> dict | None:
    node = dei.get("EntityCommonStockSharesOutstanding") or {}
    chosen: dict | None = None
    for items in (node.get("units") or {}).values():
        for item in items:
            if item.get("form") not in _FORMS or item.get("val") in (None, ""):
                continue
            if chosen is None or str(item.get("end")) > str(chosen.get("end")):
                chosen = item
    return chosen


def _instant(metric: str, row: dict, source_id: str, priority: int) -> StatedAmount:
    return StatedAmount(
        metric=metric,
        kind="instant",
        start=None,
        end=date.fromisoformat(row["end"]),
        value=Decimal(str(row["val"])),
        source_id=source_id,
        priority=priority,
    )
