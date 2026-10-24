from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.schemas.base import ResponseEnvelope
from app.api.schemas.market_data import (
    BarResponseSchema,
    InstrumentResponseSchema,
    ProviderStatusSchema,
    QuoteResponseSchema,
)
from app.services.market_data import MarketDataService

router = APIRouter(prefix="/market-data", tags=["market-data"])


def get_market_data_service() -> MarketDataService:
    """Dependency injector for MarketDataService."""
    return MarketDataService()


@router.get("/status", response_model=ResponseEnvelope[ProviderStatusSchema])
async def get_provider_status(
    service: MarketDataService = Depends(get_market_data_service),
) -> ResponseEnvelope[ProviderStatusSchema]:
    """Retrieve active market data provider health and connectivity status."""
    status = await service.get_provider_status()
    return ResponseEnvelope(data=ProviderStatusSchema(**asdict(status)))


@router.get("/quotes/{symbol}", response_model=ResponseEnvelope[QuoteResponseSchema])
async def get_quote(
    symbol: str,
    service: MarketDataService = Depends(get_market_data_service),
) -> ResponseEnvelope[QuoteResponseSchema]:
    """Retrieve normalized price quote for a given instrument symbol."""
    quote = await service.get_quote(symbol)
    return ResponseEnvelope(
        data=QuoteResponseSchema(**asdict(quote)),
        meta={"source": service.provider.name},
    )


@router.get("/history/{symbol}", response_model=ResponseEnvelope[list[BarResponseSchema]])
async def get_historical_bars(
    symbol: str,
    days: int = Query(default=30, ge=1, le=365, description="Number of past days of history to fetch"),
    interval: str = Query(default="1d", description="Bar aggregation interval (e.g. 1d)"),
    service: MarketDataService = Depends(get_market_data_service),
) -> ResponseEnvelope[list[BarResponseSchema]]:
    """Retrieve historical OHLCV bars for an instrument symbol."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    bars = await service.get_historical_bars(symbol=symbol, start=start, end=end, interval=interval)
    data = [BarResponseSchema(**asdict(bar)) for bar in bars]
    return ResponseEnvelope(
        data=data,
        meta={"source": service.provider.name, "count": len(data), "interval": interval},
    )


@router.get("/instruments", response_model=ResponseEnvelope[list[InstrumentResponseSchema]])
async def search_instruments(
    q: Optional[str] = Query(default=None, description="Search term for symbol or name"),
    service: MarketDataService = Depends(get_market_data_service),
) -> ResponseEnvelope[list[InstrumentResponseSchema]]:
    """Search and filter available financial instruments."""
    results = await service.search_instruments(q or "")
    data = [InstrumentResponseSchema(**asdict(item)) for item in results]
    return ResponseEnvelope(
        data=data,
        meta={"query": q, "count": len(data)},
    )
