from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

import yaml

from data.config import CONFIG_DIR, DATA_DIR, load_companies
from data.models import Company
from data.snapshots import SnapshotStore

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

_EXCHANGE_NAMES = {"nasdaq": "NASDAQ", "nyse": "NYSE", "cboe": "CBOE", "otc": "OTC"}
_DOMESTIC_FORMS = {"10-K", "10-Q", "10-K/A", "10-Q/A"}
_FOREIGN_FORMS = {"20-F", "40-F", "6-K", "20-F/A", "40-F/A"}

FetchJson = Callable[[str], bytes]


class CompanyNotFound(LookupError):
    pass


class AmbiguousCompany(LookupError):
    def __init__(self, query: str, candidates: list[dict[str, Any]]) -> None:
        self.candidates = candidates
        names = "; ".join(f"{c['ticker']} ({c['name']})" for c in candidates[:6])
        super().__init__(f"{query!r} matches several companies: {names}. Type the ticker.")


class ForeignFiler(LookupError):
    pass


class CompanyRegistry:
    """Turns a typed name or ticker into a full company entry, adding it to companies.yaml when new.

    Only companies whose home market is the United States are added automatically. The filing office's
    list also contains foreign companies with US listings; those are refused here because their home
    filings live elsewhere, and the data check would otherwise read the wrong cabinet.
    """

    def __init__(
        self,
        *,
        path: Path | None = None,
        store: SnapshotStore | None = None,
        fetch: FetchJson | None = None,
    ) -> None:
        self.path = path or CONFIG_DIR / "companies.yaml"
        self.store = store or SnapshotStore(DATA_DIR)
        self._fetch = fetch

    # -- public --------------------------------------------------------------

    def resolve(self, query: str) -> Company:
        known = self.find_known(query)
        if known is not None:
            return known
        match = self._lookup_sec(query)
        self._refuse_foreign(match)
        company = self._company_from_sec(match)
        self._append(company)
        return company

    def find_known(self, query: str) -> Company | None:
        wanted = _norm(query)
        companies = load_companies(self.path)
        for company in companies:
            if _norm(company.ticker) == wanted or _norm(company.local_code) == wanted:
                return company
        by_name = [c for c in companies if wanted and wanted in _norm(c.name)]
        if len(by_name) == 1:
            return by_name[0]
        return None

    # -- internals -----------------------------------------------------------

    def _fetch_bytes(self, url: str) -> bytes:
        if self._fetch is not None:
            return self._fetch(url)
        from data.providers.sec_edgar import SecEdgarProvider

        return SecEdgarProvider()._get(url)

    def _lookup_sec(self, query: str) -> dict[str, Any]:
        raw = self._fetch_bytes(SEC_TICKERS_URL)
        self.store.save_raw(
            origin="sec_edgar",
            ticker="_registry",
            filename="company_tickers_exchange.json",
            content=raw,
            url=SEC_TICKERS_URL,
            name="SEC company ticker list",
        )
        payload = json.loads(raw.decode("utf-8"))
        fields = payload["fields"]
        rows = [dict(zip(fields, row)) for row in payload["data"]]
        wanted = _norm(query)

        exact = [r for r in rows if _norm(r["ticker"]) == wanted]
        if len(exact) == 1:
            return exact[0]
        by_name = [r for r in rows if wanted and wanted in _norm(r["name"])]
        if not by_name:
            raise CompanyNotFound(
                f"{query!r} is not in the US filing office's list. Companies outside the United States "
                "(like ASML or TSMC) are added by hand in config/companies.yaml."
            )
        ciks = {r["cik"] for r in by_name}
        if len(ciks) > 1:
            by_name.sort(key=lambda r: (len(r["name"]), r["ticker"]))
            raise AmbiguousCompany(query, by_name)
        by_name.sort(key=lambda r: len(r["ticker"]))
        return by_name[0]

    def _refuse_foreign(self, match: dict[str, Any]) -> None:
        cik = f"{int(match['cik']):010d}"
        raw = self._fetch_bytes(SEC_SUBMISSIONS_URL.format(cik=cik))
        self.store.save_raw(
            origin="sec_edgar",
            ticker=str(match["ticker"]).upper(),
            filename="submissions.json",
            content=raw,
            url=SEC_SUBMISSIONS_URL.format(cik=cik),
            name="SEC EDGAR submissions",
            metadata={"kind": "submissions", "cik": cik},
        )
        forms = set(json.loads(raw.decode("utf-8")).get("filings", {}).get("recent", {}).get("form", []))
        if forms & _DOMESTIC_FORMS:
            return
        if forms & _FOREIGN_FORMS:
            raise ForeignFiler(
                f"{match['name']} files with the US office as a foreign company (forms {sorted(forms & _FOREIGN_FORMS)}). "
                "Its home market is elsewhere, so it must be added by hand with its home listing."
            )
        raise CompanyNotFound(f"{match['name']} has no quarterly or annual reports on file yet.")

    @staticmethod
    def _company_from_sec(match: dict[str, Any]) -> Company:
        ticker = str(match["ticker"]).upper()
        exchange_raw = str(match.get("exchange") or "").strip()
        exchange = _EXCHANGE_NAMES.get(exchange_raw.lower(), exchange_raw.upper() or "US")
        return Company(
            ticker=ticker,
            name=_title_case(str(match["name"])),
            cik=f"{int(match['cik']):010d}",
            region="US",
            accounting="US GAAP",
            reporting_currency="USD",
            listing=f"{exchange}:{ticker}",
            exchange=exchange,
            market_id="US",
            local_code=ticker,
            valuation_currency="USD",
            yahoo_symbol=ticker.replace(".", "-"),
            stooq_symbol=f"{ticker.lower().replace('.', '-')}.us",
            ir_release_urls=[],
            enabled_for_exp0a=True,
        )

    def _append(self, company: Company) -> None:
        payload = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {"companies": []}
        entry = company.model_dump(mode="json")
        if not company.google_symbol:
            entry.pop("google_symbol", None)
        payload.setdefault("companies", []).append(entry)
        self.path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def _title_case(name: str) -> str:
    small = {"of", "and", "the", "de", "inc", "corp", "plc", "ltd"}
    words = []
    for word in name.split():
        lowered = word.lower().strip(".,")
        if lowered in {"inc", "corp", "ltd", "llc", "plc", "co"}:
            words.append(lowered.capitalize() + ("." if lowered not in {"llc", "plc"} else ""))
        elif lowered in small:
            words.append(lowered)
        elif word.isupper() and len(word) <= 4:
            words.append(word)
        else:
            words.append(word.capitalize())
    if words:
        words[0] = words[0].capitalize() if words[0].islower() else words[0]
    return " ".join(words)
