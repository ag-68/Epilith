from datetime import date
from decimal import Decimal

from data.config import company_by_ticker
from data.markets import resolve_home_market
from data.providers.twse_mops import quarter_bounds, quarters_from_mops_series


def test_each_experiment_company_uses_its_home_market():
    nvidia = resolve_home_market(company_by_ticker("NVDA"))
    asml = resolve_home_market(company_by_ticker("ASML"))
    tsmc = resolve_home_market(company_by_ticker("TSMC"))
    assert nvidia.market.id == "US" and nvidia.uses_home_market_filings
    assert asml.market.id == "EU" and asml.uses_home_market_filings
    assert tsmc.market.id == "TW" and tsmc.uses_home_market_filings
    assert "United States" not in asml.explanation
    assert "United States" not in tsmc.explanation


def test_recognized_market_is_not_sent_to_the_us_cabinet():
    company = company_by_ticker("NVDA").model_copy(update={"ticker": "7203", "market_id": "JP", "listing": "TSE:7203"})
    resolution = resolve_home_market(company)
    assert resolution.market.name == "Japan"
    assert resolution.uses_home_market_filings is False
    assert "United States filing cabinet is not used" in resolution.explanation


def test_taiwan_series_scales_thousands_and_uses_calendar_quarters():
    content = (
        '{"xaxisList":["2026Q2"],"json":"{\\"graphData\\":[{\\"data\\":[[53, 1270380250.0, \\"C\\"]]}]}"}'
    ).encode()
    quarters = quarters_from_mops_series(content, concept="Revenue")
    assert quarters[0].start == date(2026, 4, 1)
    assert quarters[0].end == date(2026, 6, 30)
    assert quarters[0].value == Decimal("1270380250000")
    assert quarter_bounds("2026Q4") == (date(2026, 10, 1), date(2026, 12, 31))
