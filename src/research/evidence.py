from __future__ import annotations

import re

from research.models import ClaimDraft, EvidenceClaim, EvidenceDraft, EvidenceSet, SourceBundle

MIN_QUOTE_CHARS = 20
MAX_QUOTE_CHARS = 220

_QUOTE_CHARS = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u00a0": " ",
    }
)


def normalize(text: str) -> str:
    """Whitespace runs collapse and typographic quotes become plain. Nothing else changes."""
    return re.sub(r"\s+", " ", text.translate(_QUOTE_CHARS)).strip()


def quote_in_source(quote: str, source_text: str) -> bool:
    needle = normalize(quote)
    return bool(needle) and needle in normalize(source_text)


def verify_claims(draft: EvidenceDraft, bundle: SourceBundle) -> EvidenceSet:
    """Keep every claim, mark whether its quote really appears in the named source."""
    claims: list[EvidenceClaim] = []
    for index, item in enumerate(draft.claims, start=1):
        verified, note = _check(item, bundle)
        claims.append(
            EvidenceClaim(
                evidence_id=f"E{index}",
                claim=item.claim.strip(),
                exact_quote=item.exact_quote.strip(),
                source_id=item.source_id,
                verified=verified,
                note=note,
            )
        )
    return EvidenceSet(claims=claims)


def _check(item: ClaimDraft, bundle: SourceBundle) -> tuple[bool, str | None]:
    source = bundle.by_id(item.source_id)
    if source is None:
        return False, f"source_id {item.source_id!r} is not in the bundle"
    if len(normalize(item.exact_quote)) > MAX_QUOTE_CHARS:
        return False, f"quote longer than {MAX_QUOTE_CHARS} characters"
    if len(normalize(item.exact_quote)) < MIN_QUOTE_CHARS:
        return False, f"quote shorter than {MIN_QUOTE_CHARS} characters"
    if not quote_in_source(item.exact_quote, source.text):
        return False, "quote not found verbatim in the named source"
    return True, None
