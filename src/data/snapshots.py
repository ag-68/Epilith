from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from data.hashing import sha256_bytes
from data.models import Source


class SnapshotStore:
    """Append-only raw/normalized artifact store. Never overwrites a path."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.raw = root / "raw"
        self.normalized = root / "normalized"
        self.snapshots = root / "snapshots"
        for path in (self.raw, self.normalized, self.snapshots):
            path.mkdir(parents=True, exist_ok=True)

    def save_raw(
        self,
        *,
        origin: str,
        ticker: str,
        filename: str,
        content: bytes,
        url: str | None,
        metadata: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> Source:
        retrieved_at = datetime.now(timezone.utc)
        digest = sha256_bytes(content)
        stamp = retrieved_at.strftime("%Y%m%dT%H%M%SZ")
        relative = Path(origin) / ticker / f"{stamp}_{digest[:16]}_{filename}"
        path = self.raw / relative
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite snapshot {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        meta = {
            "origin": origin,
            "ticker": ticker,
            "url": url,
            "retrieved_at": retrieved_at.isoformat(),
            "content_hash": digest,
            "byte_length": len(content),
            "filename": filename,
            **(metadata or {}),
        }
        meta_path = path.with_name(path.name + ".meta.json")
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return Source(
            source_id=digest[:16],
            origin=origin,
            name=name or origin,
            url=url,
            retrieved_at=retrieved_at,
            content_hash=digest,
            raw_path=str(path),
            metadata=meta,
        )

    def latest_raw(self, origin: str, ticker: str, filename: str) -> Source | None:
        directory = self.raw / origin / ticker
        if not directory.exists():
            return None
        matches = sorted(directory.glob(f"*_{filename}"))
        if not matches:
            return None
        path = matches[-1]
        meta_path = path.with_name(path.name + ".meta.json")
        meta: dict[str, Any] = {}
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        retrieved = meta.get("retrieved_at")
        retrieved_at = (
            datetime.fromisoformat(retrieved) if retrieved else datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        )
        digest = meta.get("content_hash") or sha256_bytes(path.read_bytes())
        return Source(
            source_id=digest[:16],
            origin=origin,
            name=meta.get("name") or origin,
            url=meta.get("url"),
            retrieved_at=retrieved_at,
            content_hash=digest,
            raw_path=str(path),
            metadata=meta,
        )

    def save_normalized(self, ticker: str, snapshot_id: str, payload: dict[str, Any]) -> Path:
        path = self.normalized / ticker / f"{snapshot_id}.json"
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite snapshot {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return path
