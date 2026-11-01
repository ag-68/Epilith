import json
import shutil
from pathlib import Path

import pytest

from data.registry import (
    SEC_TICKERS_URL,
    AmbiguousCompany,
    CompanyNotFound,
    CompanyRegistry,
    ForeignFiler,
)
from data.snapshots import SnapshotStore

ROOT = Path(__file__).resolve().parents[1]

TICKERS = {
    "fields": ["cik", "name", "ticker", "exchange"],
    "data": [
        [1045810, "NVIDIA CORP", "NVDA", "Nasdaq"],
        [320193, "Apple Inc.", "AAPL", "Nasdaq"],
        [1318605, "Tesla, Inc.", "TSLA", "Nasdaq"],
        [313616, "Sony Group Corp", "SONY", "NYSE"],
        [1067983, "BERKSHIRE HATHAWAY INC", "BRK-A", "NYSE"],
        [1067983, "BERKSHIRE HATHAWAY INC", "BRK-B", "NYSE"],
        [1800, "ABBOTT LABORATORIES", "ABT", "NYSE"],
        [1551152, "AbbVie Inc.", "ABBV", "NYSE"],
    ],
}
SUBMISSIONS = {
    "0000320193": {"filings": {"recent": {"form": ["10-Q", "8-K", "10-K"]}}},
    "0000313616": {"filings": {"recent": {"form": ["6-K", "20-F", "6-K"]}}},
    "0001067983": {"filings": {"recent": {"form": ["10-K", "8-K"]}}},
}


def _fetch(url: str) -> bytes:
    if url == SEC_TICKERS_URL:
        return json.dumps(TICKERS).encode()
    cik = url.rsplit("CIK", 1)[1].split(".")[0]
    return json.dumps(SUBMISSIONS[cik]).encode()


@pytest.fixture
def registry(tmp_path: Path) -> CompanyRegistry:
    path = tmp_path / "companies.yaml"
    shutil.copy(ROOT / "config" / "companies.yaml", path)
    return CompanyRegistry(path=path, store=SnapshotStore(tmp_path / "data"), fetch=_fetch)


def test_known_company_by_ticker_name_or_local_code(registry: CompanyRegistry):
    assert registry.resolve("nvda").ticker == "NVDA"
    assert registry.resolve("NVIDIA").ticker == "NVDA"
    assert registry.resolve("Taiwan Semiconductor").ticker == "TSMC"
    assert registry.resolve("2330").ticker == "TSMC"


def test_new_us_company_is_added_to_the_address_book(registry: CompanyRegistry):
    company = registry.resolve("Apple")
    assert company.ticker == "AAPL"
    assert company.cik == "0000320193"
    assert company.listing == "NASDAQ:AAPL"
    assert company.market_id == "US" and company.valuation_currency == "USD"
    assert company.stooq_symbol == "aapl.us"
    again = CompanyRegistry(path=registry.path, store=registry.store, fetch=lambda url: (_ for _ in ()).throw(AssertionError("no fetch")))
    assert again.resolve("AAPL").name == "Apple Inc."
    assert again.resolve("NVDA").ticker == "NVDA"


def test_share_classes_of_one_company_are_not_ambiguous(registry: CompanyRegistry):
    company = registry.resolve("Berkshire Hathaway")
    assert company.ticker == "BRK-A"
    assert company.yahoo_symbol == "BRK-A"


def test_ambiguous_name_asks_for_ticker(registry: CompanyRegistry):
    with pytest.raises(AmbiguousCompany) as info:
        registry.resolve("Abb")
    assert "ABT" in str(info.value) and "ABBV" in str(info.value)


def test_foreign_filer_is_refused(registry: CompanyRegistry):
    with pytest.raises(ForeignFiler):
        registry.resolve("Sony")


def test_unknown_company_explains_the_boundary(registry: CompanyRegistry):
    with pytest.raises(CompanyNotFound) as info:
        registry.resolve("Samsung")
    assert "added by hand" in str(info.value)
