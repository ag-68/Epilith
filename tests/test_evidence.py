from datetime import datetime, timezone

from research.evidence import normalize, quote_in_source, verify_claims
from research.models import ClaimDraft, EvidenceDraft, SourceBundle, SourceExcerpt

TEXT = (
    "Data Center revenue was $41.1 billion, up 154% from a year ago.\n"
    "Demand for “Blackwell” systems  remains   strong across cloud service providers."
)


def _bundle() -> SourceBundle:
    return SourceBundle(
        bundle_id="b1",
        ticker="NVDA",
        created_at=datetime.now(timezone.utc),
        excerpts=[
            SourceExcerpt(
                source_id="rel",
                kind="ir_release",
                title="Release",
                text=TEXT,
                content_hash="x",
                path="rel.txt",
            )
        ],
    )


def test_normalize_collapses_whitespace_and_quotes():
    assert normalize("“Blackwell”  systems\n remain") == '"Blackwell" systems remain'


def test_quote_matches_across_whitespace_and_typographic_quotes():
    assert quote_in_source('Demand for "Blackwell" systems remains strong', TEXT)


def test_quote_must_be_verbatim():
    assert not quote_in_source("Data Center revenue was $41 billion", TEXT)


def test_verify_claims_marks_each_outcome():
    draft = EvidenceDraft(
        claims=[
            ClaimDraft(claim="DC grew", exact_quote="Data Center revenue was $41.1 billion, up 154% from a year ago.", source_id="rel"),
            ClaimDraft(claim="Paraphrased", exact_quote="Data Center revenue rose 154 percent year over year", source_id="rel"),
            ClaimDraft(claim="Too short", exact_quote="up 154%", source_id="rel"),
            ClaimDraft(claim="Wrong source", exact_quote="Data Center revenue was $41.1 billion, up 154%", source_id="nope"),
        ]
    )
    evidence = verify_claims(draft, _bundle())
    assert [c.evidence_id for c in evidence.claims] == ["E1", "E2", "E3", "E4"]
    assert [c.verified for c in evidence.claims] == [True, False, False, False]
    assert "not found" in evidence.claims[1].note
    assert "shorter" in evidence.claims[2].note
    assert "not in the bundle" in evidence.claims[3].note
    assert [c.evidence_id for c in evidence.verified] == ["E1"]


def test_verify_claims_rejects_a_quote_that_is_too_long():
    long_quote = "x" * 221
    draft = EvidenceDraft(claims=[ClaimDraft(claim="Long", exact_quote=long_quote, source_id="rel")])
    evidence = verify_claims(draft, _bundle())
    assert evidence.claims[0].verified is False
    assert "longer" in (evidence.claims[0].note or "")
