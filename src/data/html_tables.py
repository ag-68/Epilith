"""Turn an earnings-release page into pipe rows the statement reader understands."""

from __future__ import annotations

import re
from html.parser import HTMLParser

_CURRENCY = {"$", "€", "£", "usd", "eur", "nt$", "nt"}
_HEADER_WORD = re.compile(
    r"three months|six months|nine months|year ended|twelve months|unaudited|audited|q/q|y/y|qoq|yoy",
    re.I,
)
_DATE_WORD = re.compile(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}\b", re.I)
_YEAR_WORD = re.compile(r"^\d{4}$")


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[tuple[str, int]]]] = []
        self._table: list[list[tuple[str, int]]] | None = None
        self._row: list[tuple[str, int]] | None = None
        self._cell: list[str] | None = None
        self._span = 1

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []
            self._span = 1
            for key, value in attrs:
                if key == "colspan" and value and value.isdigit():
                    self._span = int(value)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            text = re.sub(r"\s+", " ", "".join(self._cell)).strip()
            self._row.append((text, self._span))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if any(text for text, _span in self._row):
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            if self._table:
                self.tables.append(self._table)
            self._table = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


def html_tables_to_text(html: str) -> str:
    parser = _TableParser()
    parser.feed(html)
    blocks: list[str] = []
    for table in parser.tables:
        rendered = _render_table(table)
        if not rendered:
            continue
        if "non-gaap" in rendered.lower() and "reconciliation" in rendered.lower():
            continue
        blocks.append(_section_line(rendered))
        blocks.append(rendered)
    return "\n".join(blocks)


def _section_line(rendered: str) -> str:
    lowered = rendered.lower()
    if "net cash provided" in lowered or "cash flows from operating" in lowered:
        return "Consolidated Statements of Cash Flows"
    if "total assets" in lowered or ("cash and cash equivalents" in lowered and "long-term debt" in lowered):
        return "Consolidated Balance Sheets"
    if "revenue" in lowered or "net sales" in lowered:
        return "Consolidated Statements of Operations"
    return ""


def _render_table(table: list[list[tuple[str, int]]]) -> str:
    width = max((sum(span for _text, span in row) for row in table), default=0)
    if width < 2:
        return ""
    grid = [["" for _ in range(width)] for _ in table]
    for row_index, row in enumerate(table):
        column = 0
        for text, span in row:
            span = max(span, 1)
            if column >= width:
                break
            grid[row_index][column] = text
            column += span
    drop = _currency_or_empty_columns(grid)
    header_rows = [row for row in grid if _is_header_row(row)]
    data_rows = [row for row in grid if row not in header_rows and _has_amount(row)]
    amount_cols = [
        index
        for index in range(width)
        if index not in drop and any(_is_amount_cell(row[index]) for row in data_rows)
    ]
    if not amount_cols:
        return ""
    lines: list[str] = []
    if header_rows:
        headers = [""]
        for index in amount_cols:
            parts = [row[index] for row in header_rows if row[index] and not _is_currency(row[index])]
            headers.append(" ".join(parts))
        if any(headers):
            lines.append("| " + " | ".join(headers) + " |")
    for row in data_rows:
        label = " ".join(
            row[index]
            for index in range(width)
            if index not in amount_cols and row[index] and not _is_currency(row[index]) and not _is_amount_cell(row[index])
        )
        numbers = [row[index] if not _is_currency(row[index]) else "" for index in amount_cols]
        if not label and not any(numbers):
            continue
        lines.append("| " + " | ".join([label, *numbers]) + " |")
    return "\n".join(lines)


def _currency_or_empty_columns(grid: list[list[str]]) -> set[int]:
    """Columns that only hold a currency sign are merged into the number beside them."""
    width = len(grid[0])
    drop: set[int] = set()
    for index in range(width):
        values = [row[index] for row in grid if row[index]]
        if not values:
            drop.add(index)
            continue
        if all(_is_currency(value) or _is_header_token(value) for value in values) and any(
            _is_currency(value) for value in values
        ):
            if index + 1 < width:
                for row in grid:
                    if row[index] and not _is_currency(row[index]) and not row[index + 1]:
                        row[index + 1] = row[index]
                    elif row[index] and not _is_currency(row[index]) and _is_header_token(row[index]):
                        row[index + 1] = f"{row[index]} {row[index + 1]}".strip()
            drop.add(index)
    return drop


def _is_amount_cell(text: str) -> bool:
    if not text or _YEAR_WORD.match(text.strip()) or _is_header_token(text):
        return False
    return bool(re.search(r"\d", text))


def _is_currency(text: str) -> bool:
    return text.strip().lower() in _CURRENCY


def _is_header_token(text: str) -> bool:
    return bool(_HEADER_WORD.search(text) or _DATE_WORD.search(text) or _YEAR_WORD.match(text.strip()))


def _is_header_row(row: list[str]) -> bool:
    filled = [cell for cell in row if cell and not _is_currency(cell)]
    if not filled:
        return True
    return all(_is_header_token(cell) for cell in filled)


def _has_amount(row: list[str]) -> bool:
    return any(re.search(r"\d", cell) and not _YEAR_WORD.match(cell.strip()) for cell in row)
