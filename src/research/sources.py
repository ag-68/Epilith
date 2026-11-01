from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from data.hashing import content_hash, sha256_bytes
from research.models import SourceBundle, SourceExcerpt

MANIFEST_NAME = "sources.yaml"


def load_source_bundle(folder: Path, ticker: str) -> SourceBundle:
    """Read hand-selected excerpts listed in ``sources.yaml`` and hash each file as stored."""
    manifest_path = folder / MANIFEST_NAME
    if not manifest_path.exists():
        raise FileNotFoundError(f"No {MANIFEST_NAME} in {folder}. See experiments/exp0b/sources/README.md.")
    manifest: dict[str, Any] = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    entries = manifest.get("sources") or []
    if not entries:
        raise ValueError(f"{manifest_path} lists no sources")

    excerpts: list[SourceExcerpt] = []
    seen: set[str] = set()
    for entry in entries:
        source_id = str(entry["source_id"])
        if source_id in seen:
            raise ValueError(f"Duplicate source_id {source_id!r} in {manifest_path}")
        seen.add(source_id)
        path = folder / entry["file"]
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="replace").strip()
        if not text:
            raise ValueError(f"Source file {path} is empty")
        excerpts.append(
            SourceExcerpt(
                source_id=source_id,
                kind=entry["kind"],
                title=str(entry["title"]),
                url=entry.get("url"),
                published=entry.get("published"),
                text=text,
                content_hash=sha256_bytes(raw),
                path=str(path),
            )
        )
    bundle_id = content_hash([e.content_hash for e in excerpts])[:16]
    return SourceBundle(
        bundle_id=bundle_id,
        ticker=ticker.upper(),
        excerpts=excerpts,
        created_at=datetime.now(timezone.utc),
    )
