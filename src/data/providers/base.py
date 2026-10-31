from __future__ import annotations

from typing import Protocol

from data.models import Company, Source
from data.snapshots import SnapshotStore


class FinancialDataProvider(Protocol):
    origin: str

    def fetch_company_facts(self, company: Company, store: SnapshotStore) -> tuple[Source, dict]:
        """Return stored raw source plus parsed structured payload."""


class MarketDataProvider(Protocol):
    origin: str

    def fetch_price(self, company: Company, store: SnapshotStore) -> tuple[Source, dict]:
        """Return stored raw source plus parsed quote payload."""
