from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from research.models import FactSheet, NumberFinding, RedTeamOutput, Thesis

# A number with optional thousands separators, decimals, and a scale word or percent sign.
_TOKEN = re.compile(
    r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s*(%|percent|trillion|billion|million|bn|tn|mn|x)?(?![\w.])",
    re.IGNORECASE,
)
_SCALE = {
    "trillion": Decimal("1e12"),
    "tn": Decimal("1e12"),
    "billion": Decimal("1e9"),
    "bn": Decimal("1e9"),
    "million": Decimal("1e6"),
    "mn": Decimal("1e6"),
}
_YEAR_RANGE = (1990, 2040)
_TOLERANCE = Decimal("0.01")


def fact_magnitudes(sheet: FactSheet) -> list[Decimal]:
    """Every figure the models were allowed to use, in the forms it could reasonably be written."""
    values: list[Decimal] = []
    for line in sheet.facts + sheet.excluded:
        if line.metric in {"reporting_currency", "listing", "fiscal_period"}:
            continue
        values.append(line.value)
    for key, raw in sheet.valuation.items():
        if key in {"ttm_end_date", "balance_sheet_as_of"}:
            continue
        value = Decimal(raw)
        values.append(value)
        if key == "fcf_yield":
            values.append(value * 100)
    return values


def _close(candidate: Decimal, targets: list[Decimal]) -> bool:
    for target in targets:
        if target == 0:
            continue
        for scaled in (target, target / Decimal("1e6"), target / Decimal("1e9"), target / Decimal("1e12")):
            if abs(candidate - scaled) <= abs(scaled) * _TOLERANCE:
                return True
    return False


def _prose_sections(thesis: Thesis, red_team: RedTeamOutput) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = [
        ("business", thesis.business),
        ("ai_infrastructure_exposure", thesis.ai_infrastructure_exposure),
        ("financial_interpretation", thesis.financial_interpretation),
        ("valuation_interpretation", thesis.valuation_interpretation),
        ("conclusion", thesis.conclusion.reasoning),
    ]
    sections += [("bull_thesis", t) for t in thesis.bull_thesis]
    sections += [("bear_thesis", t) for t in thesis.bear_thesis]
    sections += [("key_risks", r.description) for r in thesis.key_risks]
    # Assumption values are the model's own assumptions by design; only their rationale is scanned.
    sections += [("assumptions", a.rationale) for a in thesis.assumptions]
    sections += [("red_team", a.argument) for a in red_team.attacks]
    sections += [("red_team", red_team.overall_assessment)]
    return sections


def audit_numbers(sheet: FactSheet, thesis: Thesis, red_team: RedTeamOutput) -> list[NumberFinding]:
    """List figures in model prose that do not trace to the fact sheet. Best effort, for a human to read."""
    targets = fact_magnitudes(sheet)
    findings: list[NumberFinding] = []
    for section, text in _prose_sections(thesis, red_team):
        for match in _TOKEN.finditer(text):
            whole, fraction, suffix = match.group(1), match.group(2) or "", (match.group(3) or "").lower()
            try:
                number = Decimal(whole.replace(",", "") + fraction)
            except InvalidOperation:
                continue
            if not suffix and fraction == "" and _YEAR_RANGE[0] <= int(number) <= _YEAR_RANGE[1]:
                continue
            if not suffix and number < 10:
                continue
            scaled = number * _SCALE.get(suffix, Decimal(1))
            if _close(scaled, targets) or _close(number, targets):
                continue
            start, end = max(0, match.start() - 60), min(len(text), match.end() + 60)
            findings.append(NumberFinding(section=section, token=match.group(0).strip(), context=text[start:end].strip()))
    return findings
