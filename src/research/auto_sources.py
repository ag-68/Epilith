"""Build the analyst's reading material from the company's own filings, without a person choosing pages.

For a United States filer: the newest annual report (10-K), the quarterly report filed after it (10-Q),
and the newest earnings release (8-K exhibit). Fixed sections are cut by heading and stored as text files
with a ``sources.yaml`` manifest, in the same shape a hand-picked folder uses. The folder name is derived
from the documents' hashes and the cutting rules, so the same filings give the same folder and nothing
is rewritten.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml

from data.hashing import content_hash
from data.markets import resolve_home_market
from data.models import Company
from data.providers.sec_edgar import FilingDocument, SecEdgarProvider
from data.snapshots import SnapshotStore
from research.filing_sections import (
    RULES_VERSION,
    TEN_K_SECTIONS,
    TEN_Q_SECTIONS,
    Section,
    cut_section,
    release_text,
)
from research.models import SourceBundle
from research.sources import MANIFEST_NAME, load_source_bundle


class SourcesUnavailable(RuntimeError):
    """No automatic reading material for this company; a hand-picked folder is needed."""


def build_source_bundle(
    company: Company,
    store: SnapshotStore,
    out_root: Path,
    sec: SecEdgarProvider | None = None,
) -> tuple[SourceBundle, Path]:
    resolution = resolve_home_market(company)
    if resolution.market.filing_adapter != "sec_edgar" or not resolution.uses_home_market_filings:
        raise SourcesUnavailable(
            f"{company.name} files with {resolution.market.name}, and only United States filings are cut "
            "automatically so far. Put excerpts in experiments/exp0b/sources/"
            f"{company.ticker}/ (format in sources/README.md)."
        )
    documents = (sec or SecEdgarProvider()).latest_filing_documents(company, store)
    if not documents:
        raise SourcesUnavailable(f"No 10-K, 10-Q or earnings release could be fetched for {company.name}.")

    folder_id = content_hash([RULES_VERSION, *[doc.source.content_hash for doc in documents]])[:16]
    folder = out_root / company.ticker / folder_id
    if (folder / MANIFEST_NAME).exists():
        return load_source_bundle(folder, company.ticker), folder

    entries: list[dict[str, Any]] = []
    files: dict[str, str] = {}
    for doc in documents:
        for section in _sections(doc):
            stem = f"{doc.form.lower().replace('-', '')}_{doc.filing_date.isoformat()}_{section.spec.key}"
            files[f"{stem}.txt"] = section.text
            entries.append(
                {
                    "source_id": f"{company.ticker.lower()}-{stem}".replace("_", "-"),
                    "kind": "ir_release" if doc.form == "8-K" else "filing",
                    "title": _title(company, doc, section),
                    "url": doc.url,
                    "published": doc.filing_date,
                    "file": f"{stem}.txt",
                    "raw_path": doc.source.raw_path,
                    "raw_hash": doc.source.content_hash,
                    "section_chars": len(section.text),
                    "section_full_chars": section.full_length,
                }
            )
    if not entries:
        raise SourcesUnavailable(
            f"The filings for {company.name} were fetched, but none of the expected section headings were found."
        )

    folder.mkdir(parents=True, exist_ok=False)
    for name, text in files.items():
        (folder / name).write_text(text + "\n", encoding="utf-8")
    manifest = {
        "built_from": "sec_edgar filings, fixed sections by heading",
        "rules_version": RULES_VERSION,
        "sources": entries,
    }
    (folder / MANIFEST_NAME).write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return load_source_bundle(folder, company.ticker), folder


def _sections(doc: FilingDocument) -> list[Section]:
    if doc.form == "10-K":
        specs = TEN_K_SECTIONS
    elif doc.form == "10-Q":
        specs = TEN_Q_SECTIONS
    else:
        return [release_text(doc.text)]
    return [section for spec in specs if (section := cut_section(doc.text, spec)) is not None]


def _title(company: Company, doc: FilingDocument, section: Section) -> str:
    period = f", period ended {_fmt(doc.report_date)}" if doc.report_date else ""
    if doc.form == "8-K":
        return f"{company.name} earnings release filed {_fmt(doc.filing_date)}{period}"
    cut = " (first part)" if section.truncated else ""
    return f"{company.name} Form {doc.form}{period}, {section.spec.title}{cut}"


def _fmt(value: date) -> str:
    return value.strftime("%d %B %Y").lstrip("0")
