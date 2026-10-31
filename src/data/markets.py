from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from data.config import CONFIG_DIR, load_yaml
from data.models import Company


class HomeMarket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    region: str
    filing_adapter: str | None = None
    status: Literal["integrated", "recognized"]
    coverage: str


class MarketResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str
    market: HomeMarket
    uses_home_market_filings: bool
    explanation: str


def load_markets() -> dict[str, HomeMarket]:
    raw = load_yaml(CONFIG_DIR / "markets.yaml")
    markets = [HomeMarket.model_validate(item) for item in raw["markets"]]
    return {market.id: market for market in markets}


def resolve_home_market(company: Company) -> MarketResolution:
    """Identify where the stock is from before any filing is downloaded."""
    markets = load_markets()
    market = markets.get(company.market_id)
    if market is None:
        unknown = HomeMarket(
            id=company.market_id or "unknown",
            name=company.market_id or "unknown",
            region=company.region,
            filing_adapter=None,
            status="recognized",
            coverage="This market is not in the registry.",
        )
        return MarketResolution(
            ticker=company.ticker,
            market=unknown,
            uses_home_market_filings=False,
            explanation=(
                f"{company.ticker} is listed as {company.listing}, but market "
                f"'{company.market_id}' is not in the home-market registry. "
                "The United States filing cabinet is not used as a substitute."
            ),
        )
    integrated = market.status == "integrated" and bool(market.filing_adapter)
    if integrated:
        explanation = (
            f"{company.ticker} home market is {market.name} ({company.listing}). "
            f"Filings are read with the {market.name} adapter."
        )
    else:
        explanation = (
            f"{company.ticker} home market is {market.name} ({company.listing}). "
            f"{market.coverage.strip()} "
            "The United States filing cabinet is not used as a substitute."
        )
    return MarketResolution(
        ticker=company.ticker,
        market=market,
        uses_home_market_filings=integrated,
        explanation=explanation,
    )
