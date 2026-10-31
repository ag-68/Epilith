from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Iterable

from data.periods import (
    DurationAmount,
    QuarterAmount,
    classify_duration,
    fill_quarters,
    last_n_quarters,
)


ALLOWED_UNIT_ALIASES = {
    "money": {"USD", "EUR", "TWD", "JPY", "KRW", "CNY", "GBP"},
    "shares": {"shares", "pure"},
}


@dataclass(frozen=True)
class Observation:
    taxonomy: str
    concept: str
    unit: str
    value: Decimal
    start: date | None
    end: date
    form: str
    filed: date
    accession: str
    fy: int | None
    fp: str | None


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value[:10])


def iter_observations(
    companyfacts: dict[str, Any],
    taxonomy: str,
    concept: str,
    allowed_forms: Iterable[str],
    unit_kind: str,
    reporting_currency: str,
) -> list[Observation]:
    facts = companyfacts.get("facts", {})
    node = facts.get(taxonomy, {}).get(concept)
    if not node:
        return []
    allowed = set(allowed_forms)
    if unit_kind == "money":
        wanted_units = {reporting_currency}
    else:
        wanted_units = set(ALLOWED_UNIT_ALIASES[unit_kind])
    out: list[Observation] = []
    for unit, rows in node.get("units", {}).items():
        if unit not in wanted_units:
            continue
        for row in rows:
            form = row.get("form")
            if form not in allowed:
                continue
            end = parse_date(row.get("end"))
            filed = parse_date(row.get("filed"))
            if end is None or filed is None or row.get("val") is None:
                continue
            out.append(
                Observation(
                    taxonomy=taxonomy,
                    concept=concept,
                    unit=unit,
                    value=Decimal(str(row["val"])),
                    start=parse_date(row.get("start")),
                    end=end,
                    form=form,
                    filed=filed,
                    accession=row.get("accn") or "",
                    fy=row.get("fy"),
                    fp=row.get("fp"),
                )
            )
    return out


def dedupe_latest_filed(observations: list[Observation]) -> list[Observation]:
    best: dict[tuple[date | None, date], Observation] = {}
    conflicts: list[tuple[Observation, Observation]] = []
    for obs in observations:
        key = (obs.start, obs.end)
        current = best.get(key)
        if current is None:
            best[key] = obs
            continue
        if obs.value != current.value:
            conflicts.append((current, obs))
        if (obs.filed, obs.accession) >= (current.filed, current.accession):
            best[key] = obs
    return list(best.values())


def pick_concept(
    companyfacts: dict[str, Any],
    candidates: list[dict[str, str]],
    allowed_forms: Iterable[str],
    unit_kind: str,
    reporting_currency: str,
) -> tuple[str, str, list[Observation]] | None:
    """Pick the candidate whose latest observation is most recent.

    First-nonempty is wrong: older tags often still have history after a filer
    switches concepts (PPE vs productive assets, marketable securities vs
    current debt securities).
    """
    ranked: list[tuple[date, str, str, list[Observation]]] = []
    for candidate in candidates:
        taxonomy = candidate["taxonomy"]
        concept = candidate["concept"]
        obs = dedupe_latest_filed(
            iter_observations(
                companyfacts,
                taxonomy,
                concept,
                allowed_forms,
                unit_kind,
                reporting_currency,
            )
        )
        if obs:
            ranked.append((max(item.end for item in obs), taxonomy, concept, obs))
    if not ranked:
        return None
    ranked.sort(key=lambda item: item[0], reverse=True)
    _, taxonomy, concept, obs = ranked[0]
    return taxonomy, concept, obs


def split_durations(observations: list[Observation]) -> tuple[list[DurationAmount], list[DurationAmount], list[DurationAmount]]:
    quarterly: list[DurationAmount] = []
    ytd: list[DurationAmount] = []
    annual: list[DurationAmount] = []
    for obs in observations:
        if obs.start is None:
            continue
        amount = DurationAmount(
            start=obs.start,
            end=obs.end,
            value=obs.value,
            accession=obs.accession,
            filed=obs.filed,
            concept=obs.concept,
        )
        kind = classify_duration(obs.start, obs.end)
        if kind == "quarterly":
            quarterly.append(amount)
        elif kind == "ytd":
            ytd.append(amount)
        elif kind == "annual":
            annual.append(amount)
    return quarterly, ytd, annual


def latest_instant(observations: list[Observation]) -> Observation | None:
    instants = [obs for obs in observations if obs.start is None]
    if not instants:
        return None
    return max(instants, key=lambda o: (o.end, o.filed, o.accession))


def latest_annual(observations: list[Observation]) -> Observation | None:
    annual = [obs for obs in observations if obs.start is not None and classify_duration(obs.start, obs.end) == "annual"]
    if not annual:
        return None
    return max(annual, key=lambda o: (o.end, o.filed))


def quarter_series(observations: list[Observation], n: int = 4) -> list[QuarterAmount]:
    quarterly, ytd, annual = split_durations(observations)
    filled = fill_quarters(quarterly, ytd, annual)
    return last_n_quarters(filled, n)


def fiscal_labels(latest_quarter: QuarterAmount | None, latest_annual: Observation | None) -> dict[str, str | None]:
    labels: dict[str, str | None] = {
        "latest_quarter_end": latest_quarter.end.isoformat() if latest_quarter else None,
        "latest_quarter_start": latest_quarter.start.isoformat() if latest_quarter else None,
        "latest_fiscal_year_end": latest_annual.end.isoformat() if latest_annual else None,
        "latest_fiscal_year_start": latest_annual.start.isoformat() if latest_annual else None,
    }
    return labels
