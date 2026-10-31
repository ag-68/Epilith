from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from decimal import Decimal

import httpx

from data.http import client as http_client

from data.models import Company, Source
from data.snapshots import SnapshotStore

STOOQ_URL = "https://stooq.com/q/l/"


class StooqProvider:
    origin = "stooq"

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    def fetch_price(self, company: Company, store: SnapshotStore) -> tuple[Source, dict]:
        params = {"s": company.stooq_symbol, "f": "sd2t2ohlcv", "h": "", "e": "csv"}
        with http_client({"User-Agent": "Epilith/0.1"}, self.timeout) as client:
            response = client.get(STOOQ_URL, params=params)
            response.raise_for_status()
            content = response.content
        url = str(httpx.URL(STOOQ_URL, params=params))
        source = store.save_raw(
            origin=self.origin,
            ticker=company.ticker,
            filename="quote.csv",
            content=content,
            url=url,
            name="Stooq daily quote",
            metadata={"symbol": company.stooq_symbol},
        )
        text = content.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        row = next(reader, None)
        if not row:
            raise ValueError("Stooq returned no quote row")
        close = row.get("Close") or row.get("close")
        if close in {None, "N/D", ""}:
            raise ValueError(f"Stooq has no close price: {row}")
        date_s = row.get("Date") or row.get("date")
        time_s = row.get("Time") or row.get("time") or "00:00:00"
        as_of = datetime.fromisoformat(f"{date_s}T{time_s}").replace(tzinfo=timezone.utc)
        parsed = {
            "price": Decimal(close),
            "currency": company.valuation_currency,
            "exchange": company.exchange,
            "as_of": as_of.isoformat(),
            "market_status": "delayed_or_eod",
            "symbol": row.get("Symbol") or company.stooq_symbol,
            "raw_row": row,
        }
        return source, parsed
