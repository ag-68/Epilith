from datetime import datetime, timezone
from pathlib import Path

import pytest

from data.snapshots import SnapshotStore


def test_refuses_to_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("data.snapshots.datetime", FrozenDateTime)
    store = SnapshotStore(tmp_path)
    kwargs = dict(
        origin="test",
        ticker="NVDA",
        filename="a.bin",
        content=b"hello",
        url="https://example.com",
        name="test",
    )
    first = store.save_raw(**kwargs)
    # The same bytes again in the same second are the same snapshot, not a second write.
    same = store.save_raw(**kwargs)
    assert same.content_hash == first.content_hash and same.raw_path == first.raw_path
    assert len(list(Path(first.raw_path).parent.iterdir())) == 2  # file + meta
    Path(first.raw_path).write_bytes(b"tampered")
    with pytest.raises(FileExistsError):
        store.save_raw(**kwargs)
