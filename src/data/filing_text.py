"""Render a filed HTML document as plain text, one block element per line.

Modern filings (Workiva, Donnelley) build every paragraph and heading out of ``<div>`` and ``<span>``,
not ``<p>``. A renderer that only breaks on ``<p>`` and ``<br>`` turns a whole chapter into one line,
and headings can no longer be found at line start. This one breaks on every block-level element and
drops the hidden inline-XBRL header that sits at the top of the file.
"""

from __future__ import annotations

import re
from html import unescape

_BLOCK_END = re.compile(
    r"(?i)</(?:div|p|h[1-6]|li|ul|ol|table|tr|thead|tbody|section|article|blockquote|pre)\s*>|<br\s*/?>|<hr\s*/?>"
)
_CELL_END = re.compile(r"(?i)</t[dh]\s*>")
_DROP = re.compile(r"(?is)<(script|style|ix:header|head)\b.*?</\1\s*>")
_TAG = re.compile(r"(?s)<[^>]+>")


def filing_html_to_text(raw: str) -> str:
    text = _DROP.sub(" ", raw)
    text = _CELL_END.sub(" | ", text)
    text = _BLOCK_END.sub("\n", text)
    text = _TAG.sub(" ", text)
    text = unescape(text).replace("\xa0", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


_INDEX_ROW = re.compile(r"(?is)<tr[^>]*>(.*?)</tr>")
_INDEX_CELL = re.compile(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>")
_HREF = re.compile(r'(?i)href="([^"]+)"')


def exhibit_documents(index_html: str) -> list[tuple[str, str]]:
    """(document name, exhibit type) pairs from a filing's ``-index.htm`` page, in table order."""
    found: list[tuple[str, str]] = []
    for row in _INDEX_ROW.findall(index_html):
        cells = _INDEX_CELL.findall(row)
        if len(cells) < 4:
            continue
        href = _HREF.search(cells[2])
        if not href:
            continue
        name = href.group(1).rsplit("/", 1)[-1]
        kind = unescape(_TAG.sub("", cells[3])).strip().upper()
        found.append((name, kind))
    return found
