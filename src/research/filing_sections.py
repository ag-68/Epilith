"""Cut fixed, named sections out of a filing's text.

This is not retrieval. The sections are chosen by their printed headings ("Item 1A. Risk Factors"),
the same ones every filer must use, and each section is cut at a fixed length. Nothing is ranked or
searched. A retrieval step can replace this later without changing the pipeline downstream.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

RULES_VERSION = "sections.1"

# A heading line: optional "Part II", then "Item 1A." then a short title. Table cells become " | " in the
# text rendering, so separators are allowed around the pieces. Paragraphs that merely mention an item are
# long; headings are short, hence the length cap on the title.
_HEADING = re.compile(
    r"^\s*(?:part\s+[ivx]+\s*[.,:|\-–—]*\s*)?item\s+(\d{1,2}[a-c]?)\s*[.:|\-–—]*\s*(.{0,120})$",
    re.IGNORECASE,
)
_PAGE_NUMBER = re.compile(r"^\s*(?:\|?\s*)?\d{1,3}\s*(?:\|\s*)?$")


@dataclass(frozen=True)
class SectionSpec:
    key: str
    title: str
    item: str
    title_pattern: str
    max_chars: int


TEN_K_SECTIONS: tuple[SectionSpec, ...] = (
    SectionSpec("business", "Item 1. Business", "1", r"^business\b", 12_000),
    SectionSpec("risk_factors", "Item 1A. Risk Factors", "1a", r"^risk\s+factors\b", 15_000),
    SectionSpec("mdna", "Item 7. Management's Discussion and Analysis", "7", r"^management", 15_000),
)

TEN_Q_SECTIONS: tuple[SectionSpec, ...] = (
    SectionSpec("mdna", "Item 2. Management's Discussion and Analysis", "2", r"^management", 15_000),
    SectionSpec("risk_factors", "Item 1A. Risk Factors", "1a", r"^risk\s+factors\b", 6_000),
)

RELEASE_MAX_CHARS = 12_000


@dataclass(frozen=True)
class Section:
    spec: SectionSpec
    text: str
    full_length: int

    @property
    def truncated(self) -> bool:
        return len(self.text) < self.full_length


def clean_lines(text: str) -> list[str]:
    """Drop blank lines, page numbers and empty table cells. Keep the words as printed."""
    lines: list[str] = []
    for raw in text.splitlines():
        line = re.sub(r"(?:\s*\|\s*)+", " | ", raw).strip(" |\t")
        if not line or _PAGE_NUMBER.match(line):
            continue
        if line.lower() in {"table of contents", "index"}:
            continue
        lines.append(line)
    return lines


def _heading(lines: list[str], index: int) -> tuple[str, str] | None:
    match = _HEADING.match(lines[index].replace("|", " "))
    if not match:
        return None
    item, title = match.group(1).lower(), match.group(2).strip()
    if not title and index + 1 < len(lines) and len(lines[index + 1]) <= 120:
        # "Item 1." on one line and "Business" on the next.
        title = lines[index + 1].replace("|", " ").strip()
    return item, title


def cut_section(text: str, spec: SectionSpec) -> Section | None:
    """Return the span from the section heading to the next item heading. The table of contents also
    contains the heading; the real section is the longest candidate."""
    lines = clean_lines(text)
    headings = [(index, found) for index in range(len(lines)) if (found := _heading(lines, index))]
    title_re = re.compile(spec.title_pattern, re.IGNORECASE)
    best: tuple[int, int] | None = None
    for start, (item, title) in headings:
        if item != spec.item or not title_re.search(title):
            continue
        end = next((index for index, (other, _) in headings if index > start and other != spec.item), len(lines))
        if best is None or end - start > best[1] - best[0]:
            best = (start, end)
    if best is None:
        return None
    body = "\n".join(lines[best[0] : best[1]])
    return Section(spec=spec, text=truncate_at_paragraph(body, spec.max_chars), full_length=len(body))


def truncate_at_paragraph(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    cut = text.rfind("\n", 0, max_chars)
    if cut < max_chars // 2:
        cut = max_chars
    return text[:cut].rstrip()


def release_text(text: str, max_chars: int = RELEASE_MAX_CHARS) -> Section:
    body = "\n".join(clean_lines(text))
    spec = SectionSpec("release", "Earnings release", "", "", max_chars)
    return Section(spec=spec, text=truncate_at_paragraph(body, max_chars), full_length=len(body))
