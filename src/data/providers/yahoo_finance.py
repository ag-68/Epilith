from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import httpx

from data.http import client as http_client

from data.models import Company, Source
from data.snapshots import SnapshotStore

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"


class YahooFinanceProvider:
    origin = "yahoo_finance"

    def __init__(self, user_agent: str | None = None, timeout: float = 30.0) -> None:
        self.user_agent = user_agent or os.getenv("YAHOO_USER_AGENT", "Epilith/0.1")
        self.timeout = timeout

    def fetch_price(self, company: Company, store: SnapshotStore) -> tuple[Source, dict]:
        url = CHART_URL.format(symbol=company.yahoo_symbol)
        with http_client({"User-Agent": self.user_agent}, self.timeout) as client:
            response = client.get(url, params={"interval": "1d", "range": "5d"})
            response.raise_for_status()
            content = response.content
        source = store.save_raw(
            origin=self.origin,
            ticker=company.ticker,
            filename="chart.json",
            content=content,
            url=url,
            name="Yahoo Finance chart",
            metadata={"symbol": company.yahoo_symbol},
        )
        payload = json.loads(content.decode("utf-8"))
        result = payload["chart"]["result"][0]
        meta = result["meta"]
        timestamp = result.get("timestamp") or []
        quotes = (result.get("indicators") or {}).get("quote") or [{}]
        closes = quotes[0].get("close") or []
        price = None
        as_of = None
        for ts, close in zip(reversed(timestamp), reversed(closes)):
            if close is not None:
                price = close
                as_of = datetime.fromtimestamp(ts, tz=timezone.utc)
                break
        if price is None:
            price = meta.get("regularMarketPrice")
            as_of = datetime.fromtimestamp(meta.get("regularMarketTime"), tz=timezone.utc)
        parsed = {
            "price": price,
            "currency": meta.get("currency"),
            "exchange": meta.get("exchangeName") or meta.get("fullExchangeName"),
            "as_of": as_of.isoformat() if as_of else None,
            "market_status": meta.get("marketState") or "unknown",
            "symbol": meta.get("symbol"),
        }
        return source, parsed
