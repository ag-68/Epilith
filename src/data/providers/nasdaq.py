from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from decimal import Decimal

import httpx

from data.http import client as http_client
from data.models import Company, Source
from data.snapshots import SnapshotStore

NASDAQ_QUOTE_URL = "https://api.nasdaq.com/api/quote/{symbol}/info"


class NasdaqQuoteProvider:
    origin = "nasdaq"

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    def fetch_price(self, company: Company, store: SnapshotStore) -> tuple[Source, dict]:
        symbol = company.ticker
        url = NASDAQ_QUOTE_URL.format(symbol=symbol)
        with http_client(
            {
                "User-Agent": "Mozilla/5.0 Epilith/0.1",
                "Accept": "application/json",
            },
            self.timeout,
        ) as http:
            response = http.get(url, params={"assetclass": "stocks"})
            response.raise_for_status()
            content = response.content
        source = store.save_raw(
            origin=self.origin,
            ticker=company.ticker,
            filename="quote.json",
            content=content,
            url=str(httpx.URL(url, params={"assetclass": "stocks"})),
            name="Nasdaq official quote",
            metadata={"symbol": symbol},
        )
        payload = json.loads(content.decode("utf-8"))
        data = payload.get("data") or {}
        primary = data.get("primaryData") or {}
        price_token = str(primary.get("lastSalePrice") or "").replace("$", "").replace(",", "")
        if not price_token:
            raise ValueError(f"Nasdaq quote missing lastSalePrice: {primary}")
        as_of = _parse_nasdaq_timestamp(primary.get("lastTradeTimestamp"))
        parsed = {
            "price": Decimal(price_token),
            "currency": primary.get("currency") or company.valuation_currency,
            "exchange": data.get("exchange") or company.exchange,
            "as_of": as_of.isoformat(),
            "market_status": data.get("marketStatus") or "unknown",
            "symbol": data.get("symbol") or symbol,
            "is_real_time": primary.get("isRealTime"),
        }
        return source, parsed


def _parse_nasdaq_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    value = re.sub(r"\s+", " ", value.strip())
    for fmt in ("%b %d, %Y %I:%M %p ET", "%b %d, %Y %H:%M ET", "%b %d, %Y"):
        try:
            parsed = datetime.strptime(value.replace("EDT", "ET").replace("EST", "ET"), fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime.now(timezone.utc)
