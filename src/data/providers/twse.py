from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal

from data.http import client as http_client
from data.models import Company, Source
from data.snapshots import SnapshotStore

TWSE_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"


class TwseQuoteProvider:
    origin = "twse"

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    def fetch_price(self, company: Company, store: SnapshotStore) -> tuple[Source, dict]:
        symbol = "2330.tw"
        params = {"ex_ch": f"tse_{symbol}", "json": "1"}
        with http_client(
            {"User-Agent": "Mozilla/5.0 Epilith/0.1", "Accept": "application/json"},
            self.timeout,
        ) as http:
            response = http.get(TWSE_URL, params=params)
            response.raise_for_status()
            content = response.content
            url = str(response.request.url)
        source = store.save_raw(
            origin=self.origin,
            ticker=company.ticker,
            filename="quote.json",
            content=content,
            url=url,
            name="Taiwan Stock Exchange quote",
            metadata={"symbol": symbol},
        )
        payload = json.loads(content.decode("utf-8"))
        rows = payload.get("msgArray") or []
        if not rows:
            raise ValueError("Taiwan exchange returned no quote row")
        row = rows[0]
        price_token = row.get("pz") or row.get("z") or row.get("oa")
        if not price_token or str(price_token) in {"-", "0"}:
            raise ValueError(f"Taiwan exchange quote missing price: {row}")
        parsed = {
            "price": Decimal(str(price_token)),
            "currency": "TWD",
            "exchange": company.exchange,
            "as_of": datetime.now(timezone.utc).isoformat(),
            "market_status": "exchange_feed",
            "symbol": row.get("@") or symbol,
        }
        return source, parsed
