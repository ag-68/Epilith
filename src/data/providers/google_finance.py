from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal

from data.http import browser_headers
from data.http import client as http_client
from data.models import Company, Source
from data.snapshots import SnapshotStore

QUOTE_URL = "https://www.google.com/finance/quote/{symbol}"


class GoogleFinanceProvider:
    """Second price page for a listing. Not the same site as the primary quote."""

    origin = "google_finance"

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    def fetch_price(self, company: Company, store: SnapshotStore) -> tuple[Source, dict]:
        if not company.google_symbol:
            raise RuntimeError(f"No second-page symbol is configured for {company.ticker}.")
        url = QUOTE_URL.format(symbol=company.google_symbol)
        with http_client(browser_headers(), self.timeout) as http:
            response = http.get(url)
            response.raise_for_status()
            content = response.content
        source = store.save_raw(
            origin=self.origin,
            ticker=company.ticker,
            filename="quote.html",
            content=content,
            url=url,
            name="Google Finance quote page",
            metadata={"symbol": company.google_symbol},
        )
        text = content.decode("utf-8", errors="replace")
        if company.ticker not in text and company.local_code not in text:
            raise RuntimeError("Quote page did not mention this listing.")
        price = _price_for(text, company.valuation_currency)
        return source, {
            "price": price,
            "currency": company.valuation_currency,
            "as_of": datetime.now(timezone.utc).isoformat(),
            "market_status": "quote shown on the page; the page did not give a trade clock time",
            "symbol": company.google_symbol,
        }


def _price_for(text: str, currency: str) -> Decimal:
    if currency == "EUR":
        match = re.search(r"€\s*([0-9][0-9,]*(?:\.[0-9]+)?)", text)
    else:
        match = re.search(rf"\b{re.escape(currency)}\s*([0-9][0-9,]*(?:\.[0-9]+)?)", text)
    if match is None:
        raise RuntimeError(f"No {currency} price was shown on the quote page.")
    return Decimal(match.group(1).replace(",", ""))
