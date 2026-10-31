from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

import httpx

from data.http import client as http_client
from data.models import Company, Source
from data.snapshots import SnapshotStore

SEC_BASE = "https://data.sec.gov"
SEC_WWW = "https://www.sec.gov"


class SecEdgarProvider:
    origin = "sec_edgar"

    def __init__(self, user_agent: str | None = None, timeout: float = 60.0) -> None:
        self.user_agent = user_agent or os.getenv("SEC_USER_AGENT", "").strip()
        if not self.user_agent or "@" not in self.user_agent:
            raise RuntimeError(
                "SEC_USER_AGENT must be set in the environment and include a contact email. "
                "See .env.example."
            )
        self.timeout = timeout

    def _client(self) -> httpx.Client:
        return http_client(
            {
                "User-Agent": self.user_agent,
                "Accept": "application/json, text/html, */*",
                "Accept-Encoding": "gzip, deflate",
            },
            self.timeout,
        )

    def _get(self, url: str) -> bytes:
        time.sleep(0.15)
        with self._client() as client:
            response = client.get(url)
            response.raise_for_status()
            return response.content

    def fetch_company_facts(self, company: Company, store: SnapshotStore) -> tuple[Source, dict]:
        url = f"{SEC_BASE}/api/xbrl/companyfacts/CIK{company.cik}.json"
        try:
            content = self._get(url)
        except httpx.HTTPError as exc:
            cached = store.latest_raw(self.origin, company.ticker, "companyfacts.json")
            if cached and cached.raw_path:
                cached = cached.model_copy(
                    update={
                        "metadata": {
                            **cached.metadata,
                            "live_fetch_error": str(exc),
                            "used_cached_raw": True,
                        }
                    }
                )
                payload = Path(cached.raw_path).read_bytes()
                return cached, json.loads(payload.decode("utf-8"))
            raise
        source = store.save_raw(
            origin=self.origin,
            ticker=company.ticker,
            filename="companyfacts.json",
            content=content,
            url=url,
            name="SEC EDGAR companyfacts XBRL",
            metadata={"kind": "companyfacts", "cik": company.cik},
        )
        return source, json.loads(content.decode("utf-8"))

    def fetch_submissions(self, company: Company, store: SnapshotStore) -> tuple[Source, dict]:
        url = f"{SEC_BASE}/submissions/CIK{company.cik}.json"
        content = self._get(url)
        source = store.save_raw(
            origin=self.origin,
            ticker=company.ticker,
            filename="submissions.json",
            content=content,
            url=url,
            name="SEC EDGAR submissions",
            metadata={"kind": "submissions", "cik": company.cik},
        )
        return source, json.loads(content.decode("utf-8"))

    def fetch_url(self, company: Company, store: SnapshotStore, url: str, filename: str, name: str) -> Source:
        content = self._get(url)
        return store.save_raw(
            origin=self.origin,
            ticker=company.ticker,
            filename=filename,
            content=content,
            url=url,
            name=name,
            metadata={"kind": "filing_document"},
        )

    def latest_earnings_exhibits(
        self,
        company: Company,
        store: SnapshotStore,
        limit: int = 6,
    ) -> list[tuple[Source, str]]:
        """Download recent 8-K EX-99.1 style exhibits (earnings releases)."""
        try:
            _, submissions = self.fetch_submissions(company, store)
        except httpx.HTTPError:
            return []
        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        exhibits: list[tuple[Source, str]] = []
        cik_nolead = str(int(company.cik))
        for form, accn, primary in zip(forms, accessions, primary_docs):
            if form not in {"8-K", "8-K/A", "6-K"}:
                continue
            accn_nodash = accn.replace("-", "")
            index_url = f"{SEC_WWW}/Archives/edgar/data/{cik_nolead}/{accn_nodash}/{accn}-index.json"
            try:
                index_source = self.fetch_url(
                    company,
                    store,
                    index_url,
                    f"{accn}-index.json",
                    "SEC filing index",
                )
                index = json.loads(_read_text(index_source.raw_path))
            except Exception:
                # Fallback: try the primary document itself.
                url = f"{SEC_WWW}/Archives/edgar/data/{cik_nolead}/{accn_nodash}/{primary}"
                try:
                    source = self.fetch_url(company, store, url, primary, f"{form} primary document")
                except httpx.HTTPError:
                    continue
                exhibits.append((source, _read_text(source.raw_path)))
                if len(exhibits) >= limit:
                    break
                continue
            directory = index.get("directory", {}).get("item", [])
            chosen = _choose_exhibit(directory, primary)
            if not chosen:
                continue
            url = f"{SEC_WWW}/Archives/edgar/data/{cik_nolead}/{accn_nodash}/{chosen}"
            try:
                source = self.fetch_url(company, store, url, chosen, f"{form} exhibit {chosen}")
            except httpx.HTTPError:
                continue
            exhibits.append((source, _read_text(source.raw_path)))
            if len(exhibits) >= limit:
                break
        return exhibits


def _read_text(path: str | None) -> str:
    if not path:
        raise FileNotFoundError("missing raw path")
    return Path(path).read_text(encoding="utf-8", errors="replace")


def _choose_exhibit(items: list[dict[str, Any]], primary: str) -> str | None:
    names = [item.get("name", "") for item in items if item.get("name")]
    preferred = [
        n
        for n in names
        if re.search(r"ex[-_]?99", n, re.I)
        or re.search(r"exhibit99", n, re.I)
        or "earnings" in n.lower()
        or "press" in n.lower()
    ]
    html = [n for n in preferred if n.lower().endswith((".htm", ".html"))]
    if html:
        return html[0]
    if preferred:
        return preferred[0]
    if primary:
        return primary
    return None
