from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from data.hashing import content_hash, stable_id
from data.models import Company, MarketFact, Source


PRICE_DEFINITION = (
    "Last available trade/quote for the local primary listing. "
    "The as-of timestamp is required; the price is not called current without it."
)


def market_fact_from_quote(company: Company, source: Source, parsed: dict) -> MarketFact:
    price = Decimal(str(parsed["price"]))
    as_of = parsed["as_of"]
    if isinstance(as_of, str):
        as_of_ts = datetime.fromisoformat(as_of)
    else:
        as_of_ts = as_of
    payload = {
        "ticker": company.ticker,
        "price": price,
        "currency": parsed.get("currency") or company.valuation_currency,
        "listing": company.listing,
        "as_of": as_of_ts.isoformat(),
        "source_id": source.source_id,
    }
    digest = content_hash(payload)
    return MarketFact(
        fact_id=stable_id(company.ticker, "price", source.origin, digest[:12]),
        price=price,
        currency=payload["currency"],
        listing=company.listing,
        as_of_timestamp=as_of_ts,
        market_status=str(parsed.get("market_status") or "unknown"),
        source_id=source.source_id,
        retrieved_at=source.retrieved_at,
        content_hash=digest,
        definition=PRICE_DEFINITION,
    )
