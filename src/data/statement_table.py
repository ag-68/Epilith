"""Read quarterly tables from a company report.

A twelve-month total used as a second source is either the sum of four quarters
from another document, or another document's full year plus this year's
year-to-date minus last year's year-to-date. Quarters from the first source
are not copied in to fill a gap.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

NUMBER_RE = re.compile(r"\((?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?\)|(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?")
VALUE_TOKEN_RE = re.compile(
    r"\((?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?\)|(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?|—|–|(?<!\w)-(?!\w)"
)
QUARTER_CODE_RE = re.compile(r"\b([1-4])Q\s+(20\d{2})\b", re.I)
MONTH_DAY_RE = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})\b", re.I)
YEAR_RE = re.compile(r"\b(20\d{2})\b")
SIX_MONTH_RE = re.compile(r"\b(?:six|6)\s+months(?:\s+ended)?(?:\s+20\d{2})?\b", re.I)
UNIT_TOKEN_RE = re.compile(r"USD|NTD|EUR|%", re.I)


@dataclass(frozen=True)
class StatedAmount:
    metric: str
    kind: str
    start: date | None
    end: date
    value: Decimal
    source_id: str = ""
    priority: int = 1
    accounting: str = ""


@dataclass(frozen=True)
class Slot:
    take: bool
    kind: str
    end: date | None
    start: date | None
    unit: str


def sum_independent_quarters(
    amounts: list[StatedAmount],
    metric: str,
    primary_source_ids: set[str],
    n: int = 4,
    end_on: date | None = None,
) -> tuple[Decimal, str, date, date] | None:
    """Sum n quarters from documents that are not the primary source.

    When end_on is set, the window ends on that date. A newer quarter in the
    company report is not mixed into an older twelve-month total.
    """
    rows = [
        item
        for item in amounts
        if item.metric == metric and item.kind == "quarter" and item.source_id not in primary_source_ids
    ]
    by_end: dict[date, StatedAmount] = {}
    for item in rows:
        current = by_end.get(item.end)
        if current is None or item.priority > current.priority:
            by_end[item.end] = item
            continue
        if item.priority < current.priority or current.value == 0:
            continue
        gap = abs(item.value - current.value) / abs(current.value)
        if gap > Decimal("0.01"):
            continue
    if end_on is not None:
        by_end = {end: item for end, item in by_end.items() if end <= end_on or abs((end - end_on).days) <= 5}
        if not by_end or abs((max(by_end) - end_on).days) > 5:
            return None
    if len(by_end) < n:
        return None
    chosen = [by_end[end] for end in sorted(by_end)[-n:]]
    newest = chosen[-1]
    start = chosen[0].start or chosen[0].end
    return sum((item.value for item in chosen), Decimal("0")), newest.source_id, start, newest.end


def collapse_amounts(amounts: list[StatedAmount], metric: str, kind: str) -> list[StatedAmount]:
    """One value per period end. A more specific line, such as profit of the parent, wins."""
    by_end: dict[date, StatedAmount] = {}
    for item in amounts:
        if item.metric != metric or item.kind != kind:
            continue
        current = by_end.get(item.end)
        if current is None or item.priority > current.priority:
            by_end[item.end] = item
    return [by_end[end] for end in sorted(by_end)]


def latest_independent_point(
    amounts: list[StatedAmount],
    metric: str,
    primary_source_ids: set[str],
    as_of: date | None = None,
) -> tuple[Decimal, str, date] | None:
    rows = [
        item
        for item in amounts
        if item.metric == metric and item.kind == "instant" and item.source_id not in primary_source_ids
    ]
    if as_of is not None:
        rows = [item for item in rows if abs((item.end - as_of).days) <= 5]
    if not rows:
        return None
    chosen = max(rows, key=lambda item: (item.end, item.priority))
    return chosen.value, chosen.source_id, chosen.end


def parse_statement_text(text: str, reporting_currency: str, source_id: str = "") -> list[StatedAmount]:
    scale = _document_scale(text)
    lines = text.splitlines()
    found: list[StatedAmount] = []
    section = "other"
    purchases = False
    layout: list[Slot] | None = None
    pending_label = ""
    index = 0
    while index < len(lines):
        raw = lines[index].strip()
        if not raw:
            index += 1
            continue
        section, purchases = _update_section(raw, section, purchases)
        blob, consumed = _header_blob(lines, index)
        if blob:
            replacement = _layout_from_header(blob, section)
            index += consumed
            if replacement:
                layout = replacement
                if index < len(lines) and _is_unit_line(lines[index]):
                    layout = _apply_units(layout, lines[index], reporting_currency)
                    index += 1
            continue
        if layout is None:
            index += 1
            continue
        raw, pending_label = _merge_wrapped_label(raw, pending_label)
        if pending_label and raw == "":
            index += 1
            continue
        found.extend(_row_amounts(raw, layout, section, purchases, scale, reporting_currency, source_id))
        index += 1
    return _with_total_debt(found)


def _header_blob(lines: list[str], index: int) -> tuple[str | None, int]:
    split, consumed = _split_column_header(lines, index)
    if split:
        return split, consumed
    line = lines[index].strip()
    if not _looks_like_header(line):
        return None, 0
    blob = line
    consumed = 1
    look = index + 1
    while look < len(lines) and not lines[look].strip():
        look += 1
    if look < len(lines):
        nxt = lines[look].strip()
        if (
            len(MONTH_DAY_RE.findall(line)) >= 2
            and not YEAR_RE.search(line)
            and len(YEAR_RE.findall(nxt)) >= 2
            and not MONTH_DAY_RE.search(nxt)
            and not _looks_like_header(nxt)
        ):
            blob = f"{line} {nxt}"
            consumed = look - index + 1
    return blob, consumed


def _split_column_header(lines: list[str], index: int) -> tuple[str | None, int]:
    """Join a header that puts each period on its own line."""
    parts: list[str] = []
    look = index
    while look < len(lines) and look < index + 16:
        line = lines[look].strip()
        if not line:
            look += 1
            continue
        if re.fullmatch(r"\(?unaudited\)?|\(?audited\)?", line, re.I):
            look += 1
            continue
        if re.fullmatch(r"20\d{2}", line) or re.fullmatch(r"[1-4]Q\s+20\d{2}", line, re.I):
            parts.append(line)
            look += 1
            continue
        break
    if len(parts) < 2:
        return None, 0
    return " ".join(parts), look - index


def _looks_like_header(line: str) -> bool:
    if QUARTER_CODE_RE.search(line) and len(QUARTER_CODE_RE.findall(line)) >= 2:
        return True
    if SIX_MONTH_RE.search(line) and (QUARTER_CODE_RE.search(line) or len(MONTH_DAY_RE.findall(line)) >= 2):
        return True
    if len(MONTH_DAY_RE.findall(line)) >= 2 and (
        re.search(r"three months|six months|balance sheet|unaudited", line, re.I) or "," in line
    ):
        return True
    return False


def _is_unit_line(line: str) -> bool:
    tokens = UNIT_TOKEN_RE.findall(line)
    if len(tokens) < 2:
        return False
    leftover = UNIT_TOKEN_RE.sub(" ", line)
    words = re.findall(r"[A-Za-z]{2,}", leftover)
    return len(words) <= 1


def _layout_from_header(blob: str, section: str) -> list[Slot] | None:
    periods = _periods_in_header(blob, section)
    if len(periods) < 2:
        return None
    return [
        Slot(take=item[0] != "change", kind=item[0], end=item[1], start=item[2], unit="VALUE")
        for item in periods
    ]


def _periods_in_header(blob: str, section: str) -> list[tuple[str, date | None, date | None]]:
    """Return (kind, end, start) in column order. kind is quarter, ytd, instant, or change."""
    if QUARTER_CODE_RE.search(blob):
        periods: list[tuple[str, date | None, date | None]] = []
        pattern = re.compile(
            r"\b(?:six|6)\s+months(?:\s+(20\d{2}))?"
            r"|\b([1-4])Q\s+(20\d{2})\b"
            r"|\b(20\d{2})\b"
            r"|\b(QoQ|YoY)\b",
            re.I,
        )
        for match in pattern.finditer(blob):
            if match.group(0).lower().startswith("six") or match.group(0).lower().startswith("6"):
                year = int(match.group(1) or YEAR_RE.search(blob).group(1))
                periods.append(("ytd", date(year, 6, 30), date(year, 1, 1)))
            elif match.group(2):
                quarter = int(match.group(2))
                year = int(match.group(3))
                start, end = _calendar_quarter(year, quarter)
                periods.append(("quarter", end, start))
            elif match.group(4):
                year = int(match.group(4))
                periods.append(("ytd", date(year, 12, 31), date(year, 1, 1)))
            else:
                periods.append(("change", None, None))
        return periods

    month_days = [(MONTHS[name[:3].lower()], int(day)) for name, day in MONTH_DAY_RE.findall(blob)]
    years = [int(year) for year in YEAR_RE.findall(blob)]
    if len(month_days) >= 2 and len(years) >= len(month_days):
        years = years[-len(month_days) :]
        lowered = blob.lower()
        three = "three months" in lowered
        six = "six months" in lowered
        year_ended = "year ended" in lowered or "twelve months" in lowered
        periods = []
        previous_end: date | None = None
        for index, ((month, day), year) in enumerate(zip(month_days, years)):
            end = date(year, month, day)
            later_half = index >= len(month_days) // 2
            if three and six and later_half:
                kind = "ytd"
                start = _shift_months(end, -6)
            elif three and year_ended and later_half:
                kind = "annual"
                start = _shift_months(end, -12)
            elif year_ended and not three:
                kind = "annual"
                start = _shift_months(end, -12)
            elif three or (six and not three):
                kind = "ytd" if six and not three else "quarter"
                if kind == "quarter" and previous_end is not None:
                    start = date.fromordinal(previous_end.toordinal() + 1)
                else:
                    start = _shift_months(end, -3 if kind == "quarter" else -6)
            else:
                kind = "instant"
                start = None
            periods.append((kind, end, start))
            if kind == "quarter":
                previous_end = end
        if re.search(r"\bQoQ\b", blob, re.I):
            periods.append(("change", None, None))
        if re.search(r"\bYoY\b", blob, re.I):
            periods.append(("change", None, None))
        return periods
    return []


def _apply_units(layout: list[Slot], unit_line: str, reporting_currency: str) -> list[Slot]:
    tokens = [token.upper() for token in UNIT_TOKEN_RE.findall(unit_line)]
    if not tokens:
        return layout
    wanted = {"TWD": "NTD", "USD": "USD", "EUR": "EUR"}.get(reporting_currency, "NTD")
    expanded: list[Slot] = []
    cursor = 0
    for index, slot in enumerate(layout):
        if cursor >= len(tokens):
            break
        group = [tokens[cursor]]
        cursor += 1
        if index == 0 and cursor < len(tokens) and tokens[cursor] in {"USD", "NTD", "EUR"} and tokens[cursor] != group[0]:
            group.append(tokens[cursor])
            cursor += 1
        if cursor < len(tokens) and tokens[cursor] == "%":
            group.append("%")
            cursor += 1
        for unit in group:
            take = slot.take and unit == wanted
            expanded.append(Slot(take=take, kind=slot.kind, end=slot.end, start=slot.start, unit=unit))
    return expanded or layout


def _row_amounts(
    line: str,
    layout: list[Slot],
    section: str,
    purchases: bool,
    scale: Decimal,
    reporting_currency: str,
    source_id: str,
) -> list[StatedAmount]:
    label, numbers = _split_row(line)
    if not label or not numbers or len(numbers) != len(layout):
        return []
    metric, priority = _metric_for(label, section, purchases)
    if metric is None:
        return []
    found: list[StatedAmount] = []
    for slot, number in zip(layout, numbers):
        if not slot.take or slot.end is None or number is None:
            continue
        value = number * scale
        if metric == "capex":
            value = abs(value)
        found.append(
            StatedAmount(
                metric=metric,
                kind=slot.kind if slot.kind != "ytd" else "ytd",
                start=slot.start,
                end=slot.end,
                value=value,
                source_id=source_id,
                priority=priority,
            )
        )
    return found


def _merge_wrapped_label(line: str, pending: str) -> tuple[str, str]:
    """Join a label that the report split across two table rows."""
    if "|" not in line:
        if pending:
            return f"{pending} {line}".strip(), ""
        return line, ""
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    if len(cells) >= 2 and all(cell in {"", "—", "–", "-"} for cell in cells[1:]):
        return "", f"{pending} {cells[0]}".strip()
    if pending and cells:
        cells[0] = f"{pending} {cells[0]}".strip()
        return "| " + " | ".join(cells) + " |", ""
    return line, pending


def _split_row(line: str) -> tuple[str, list[Decimal | None]]:
    if "|" in line:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            return "", []
        numbers: list[Decimal | None] = []
        for cell in cells[1:]:
            if cell in {"", "—", "–", "-", "–"}:
                numbers.append(None)
                continue
            parsed = _numbers_in(cell)
            numbers.append(parsed[0] if parsed else None)
        return cells[0], numbers
    match = VALUE_TOKEN_RE.search(line)
    if match is None:
        return "", []
    label = re.sub(r"[$€£]", " ", line[: match.start()])
    label = re.sub(r"\s+", " ", label).strip(" :-")
    values: list[Decimal | None] = []
    for token in VALUE_TOKEN_RE.findall(line):
        if token in {"-", "—", "–"}:
            values.append(None)
            continue
        values.append(_numbers_in(token)[0])
    return label, values


def _numbers_in(text: str) -> list[Decimal | None]:
    found: list[Decimal | None] = []
    for match in NUMBER_RE.finditer(text):
        token = match.group(0)
        negative = token.startswith("(")
        cleaned = token.replace("(", "").replace(")", "").replace(",", "")
        value = Decimal(cleaned)
        found.append(-value if negative else value)
    return found


def _metric_for(label: str, section: str, purchases: bool) -> tuple[str | None, int]:
    lab = re.sub(r"\s+", " ", label).strip(" :-").lower()
    if not lab or "per share" in lab or "percentage" in lab or "margin" in lab:
        return None, 1
    if lab in {"shareholders of the parent", "shareholders of the parent company"} or "attributable to shareholders of the parent" in lab:
        return "net_income", 2
    if re.search(r"total net sales|^net revenue$|^revenue$", lab):
        return "revenue", 1
    if lab in {"income from operations", "operating income"}:
        return "operating_income", 1
    if lab == "net income":
        return "net_income", 1
    if section == "cash" and "investing" not in lab and "financing" not in lab and "net income" not in lab:
        if lab in {
            "net cash provided by (used in) operating activities",
            "net cash provided by operating activities",
            "net cash generated by operating activities",
            "operating activities",
        }:
            return "operating_cash_flow", 1
    if re.search(r"purchase of property, plant and equipment$", lab):
        return "capex", 1
    if "purchases related to property and equipment" in lab or "purchases of property and equipment" in lab:
        return "capex", 1
    if section == "cash" and purchases and lab == "property, plant and equipment":
        return "capex", 1
    if section == "balance" and lab.startswith("cash and cash equivalents") and "beginning" not in lab and "end of" not in lab:
        return "cash", 1
    if section == "balance" and (
        "current portion of bonds" in lab
        or "current portion of long-term" in lab
        or lab == "short-term debt"
    ):
        return "debt_current", 1
    if section == "balance" and lab in {"bonds payable", "long-term debt"}:
        return "debt_noncurrent", 1
    if "capital stock" in lab and "surplus" not in lab and "par" in lab:
        return "capital_stock", 1
    return None, 1


def _with_total_debt(amounts: list[StatedAmount]) -> list[StatedAmount]:
    pieces = [item for item in amounts if item.metric in {"debt_current", "debt_noncurrent"}]
    if not pieces:
        return amounts
    by_key: dict[tuple[date, str], dict[str, StatedAmount]] = {}
    for item in pieces:
        by_key.setdefault((item.end, item.source_id), {})[item.metric] = item
    combined = list(amounts)
    for (end, source_id), parts in by_key.items():
        current = parts.get("debt_current")
        noncurrent = parts.get("debt_noncurrent")
        if current and noncurrent:
            value = current.value + noncurrent.value
        elif noncurrent:
            value = noncurrent.value
        else:
            continue
        combined.append(
            StatedAmount(
                metric="total_debt",
                kind="instant",
                start=None,
                end=end,
                value=value,
                source_id=source_id,
                priority=2 if current and noncurrent else 1,
            )
        )
    return combined


def _update_section(line: str, section: str, purchases: bool) -> tuple[str, bool]:
    lowered = line.lower()
    if "balance sheet" in lowered:
        return "balance", False
    if "cash flow" in lowered:
        return "cash", False
    if "statement of operations" in lowered or "statements of operations" in lowered or "comprehensive income" in lowered:
        return "income", False
    if "ratios" in lowered or "forward-looking" in lowered or "forward looking" in lowered:
        return "other", False
    if "reconciliation" in lowered and "non-gaap" in lowered:
        return "other", False
    if section == "cash" and "acquisitions of" in lowered:
        return section, True
    if section == "cash" and ("proceeds from" in lowered or "net cash used" in lowered or "cash flows from financing" in lowered):
        return section, False
    return section, purchases


def _document_scale(text: str) -> Decimal:
    lowered = text.lower()
    if re.search(r"in millions|expressed in millions|\$ in millions|€,\s*in millions", lowered):
        return Decimal("1000000")
    if re.search(r"in thousands|expressed in thousands", lowered):
        return Decimal("1000")
    return Decimal("1")


def _calendar_quarter(year: int, quarter: int) -> tuple[date, date]:
    start_month = (quarter - 1) * 3 + 1
    end_month = start_month + 2
    last_day = calendar.monthrange(year, end_month)[1]
    return date(year, start_month, 1), date(year, end_month, last_day)


def stated_year_total(
    amounts: list[StatedAmount],
    metric: str,
    start: date,
    end: date,
) -> tuple[Decimal, str] | None:
    """One document's own full year: a year column, or a half-year plus the later quarters."""
    rows = [item for item in amounts if item.metric == metric and item.source_id]
    covered = [
        item
        for item in rows
        if item.kind in {"annual", "ytd"}
        and item.start is not None
        and abs((item.start - start).days) <= 5
        and abs((item.end - end).days) <= 5
    ]
    if covered:
        chosen = max(covered, key=lambda item: item.priority)
        return chosen.value, chosen.source_id
    openers = [
        item
        for item in rows
        if item.kind == "ytd"
        and item.start is not None
        and abs((item.start - start).days) <= 5
        and item.end < end
    ]
    if not openers:
        return None
    opener = max(openers, key=lambda item: item.end)
    quarters = [
        item
        for item in rows
        if item.kind == "quarter" and item.source_id == opener.source_id and opener.end < item.end <= end
    ]
    by_end: dict[date, StatedAmount] = {}
    for item in quarters:
        current = by_end.get(item.end)
        if current is None or item.priority > current.priority:
            by_end[item.end] = item
    if not by_end or abs((max(by_end) - end).days) > 5:
        return None
    total = opener.value + sum((item.value for item in by_end.values()), Decimal("0"))
    return total, opener.source_id


def ttm_candidates_from_annual_and_ytd(
    amounts: list[StatedAmount],
    metric: str,
    primary_source_ids: set[str],
    end_on: date,
) -> list[tuple[Decimal, str]]:
    """Full year from another document, plus this year-to-date, minus last year's.

    The full year and both year-to-date columns have to come from a different
    document than the twelve-month total. Year-to-date taken from that same
    statement cancels out of the formula and does not check its newest half.
    """
    current_rows = [
        item
        for item in amounts
        if item.metric == metric
        and item.kind == "ytd"
        and item.source_id not in primary_source_ids
        and abs((item.end - end_on).days) <= 5
    ]
    if not current_rows:
        return []
    current = max(current_rows, key=lambda item: item.priority)
    try:
        prior_end = date(end_on.year - 1, end_on.month, end_on.day)
    except ValueError:
        prior_end = date(end_on.year - 1, end_on.month, 28)
    prior_rows = [
        item
        for item in amounts
        if item.metric == metric
        and item.kind == "ytd"
        and item.source_id not in primary_source_ids
        and abs((item.end - prior_end).days) <= 5
    ]
    if not prior_rows:
        return []
    prior = max(prior_rows, key=lambda item: item.priority)
    found: list[tuple[Decimal, str]] = []
    seen: set[str] = set()
    for annual in amounts:
        if annual.metric != metric or annual.kind != "annual":
            continue
        if not annual.source_id or annual.source_id in primary_source_ids or annual.source_id in seen:
            continue
        if annual.end <= prior.end or annual.end > current.end:
            continue
        seen.add(annual.source_id)
        found.append((annual.value + current.value - prior.value, annual.source_id))
    return found


def _shift_months(end: date, months: int) -> date:
    month = end.month + months
    year = end.year
    while month <= 0:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    last_day = calendar.monthrange(year, month)[1]
    start = date(year, month, min(end.day, last_day))
    return date.fromordinal(start.toordinal() + 1)
