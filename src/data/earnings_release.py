from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from html import unescape
from typing import Any


SCALE = {
    "billion": Decimal("1000000000"),
    "billions": Decimal("1000000000"),
    "million": Decimal("1000000"),
    "millions": Decimal("1000000"),
}

LABELS = {
    "revenue": [r"revenue"],
    "operating_income": [r"operating income", r"income from operations"],
    "net_income": [r"net income"],
    "operating_cash_flow": [r"net cash provided by operating activities"],
    "capex": [
        r"purchases related to property and equipment",
        r"purchases of property, plant and equipment",
        r"payments to acquire property",
    ],
    "cash": [r"cash and cash equivalents"],
    "short_term_debt": [r"short-term debt"],
    "long_term_debt": [r"long-term debt"],
}


def html_to_text(raw: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p>", "\n", text)
    text = re.sub(r"(?i)</tr>", "\n", text)
    text = re.sub(r"(?i)</t[dh]>", " | ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text


def _parse_number(token: str, scale: Decimal | None = None) -> Decimal | None:
    cleaned = token.replace(",", "").replace("(", "-").replace(")", "")
    cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
    if cleaned in {"", "-", ".", "-."}:
        return None
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    if scale is not None:
        return value * scale
    return value


def infer_document_scale(text: str) -> Decimal | None:
    lowered = text.lower()
    if re.search(r"in millions|\$ in millions|\(in millions\)|\(millions\)", lowered):
        return Decimal("1000000")
    if re.search(r"in billions|\$ in billions|\(in billions\)|\(billions\)", lowered):
        return Decimal("1000000000")
    return None


def extract_metrics(raw: str) -> dict[str, dict[str, Any]]:
    text = html_to_text(raw)
    scale = infer_document_scale(text)
    found: dict[str, dict[str, Any]] = {}
    for metric, patterns in LABELS.items():
        for pattern in patterns:
            regex = re.compile(
                rf"(?is)({pattern})(?:[^0-9]{{0,30}}(?:19|20)\d{{2}})?[^0-9]{{0,80}}"
                rf"\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(billion|million|billions|millions)?",
            )
            match = regex.search(text)
            if not match:
                continue
            unit_word = (match.group(3) or "").lower()
            raw_number = match.group(2).replace(",", "")
            if not unit_word and re.fullmatch(r"19\d\d|20\d\d", raw_number):
                continue
            local_scale = SCALE.get(unit_word, scale)
            value = _parse_number(match.group(2), local_scale)
            if value is None:
                continue
            found[metric] = {
                "value": value,
                "quote": re.sub(r"\s+", " ", match.group(0)).strip(),
                "label": match.group(1),
            }
            break
    if "short_term_debt" in found and "long_term_debt" in found:
        found["total_debt"] = {
            "value": found["short_term_debt"]["value"] + found["long_term_debt"]["value"],
            "quote": "short-term debt + long-term debt from IR balance sheet",
            "label": "total_debt",
        }
    return found
