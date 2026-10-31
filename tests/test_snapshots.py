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
    store.save_raw(**kwargs)
    with pytest.raises(FileExistsError):
        store.save_raw(**kwargs)
