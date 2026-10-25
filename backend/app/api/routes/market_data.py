from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas.base import ResponseEnvelope
from app.api.schemas.market_data import (
    BackfillRequestSchema,
    BackfillResponseSchema,
    BarResponseSchema,
    InstrumentResponseSchema,
    PersistedPriceSchema,
    ProviderStatusSchema,
    QuoteResponseSchema,
    SyncCatalogRequestSchema,
    SyncCatalogResponseSchema,
)
from app.database.session import get_db
from app.services.ingestion import MarketDataIngestionService
from app.services.market_data import MarketDataService

router = APIRouter(prefix="/market-data", tags=["market-data"])


def get_market_data_service() -> MarketDataService:
    """Dependency injector for MarketDataService."""
    return MarketDataService()


def get_ingestion_service(
    db: Session = Depends(get_db),
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> MarketDataIngestionService:
    """Dependency injector for MarketDataIngestionService."""
    return MarketDataIngestionService(db=db, market_data_service=market_data_service)


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


@router.post("/ingest/quote/{symbol}", response_model=ResponseEnvelope[PersistedPriceSchema])
async def ingest_quote(
    symbol: str,
    interval: str = Query(default="tick", description="Observation interval identifier"),
    service: MarketDataIngestionService = Depends(get_ingestion_service),
) -> ResponseEnvelope[PersistedPriceSchema]:
    """Fetch live quote from active provider and persist observation into database."""
    price = await service.ingest_quote(symbol=symbol, interval=interval)
    data = PersistedPriceSchema(
        id=price.id,
        instrument_id=price.instrument_id,
        timestamp=price.timestamp,
        price=price.price,
        open=price.open,
        high=price.high,
        low=price.low,
        close=price.close,
        volume=price.volume,
        currency=price.currency,
        interval=price.interval,
        source=price.source,
        created_at=price.created_at,
    )
    return ResponseEnvelope(
        data=data,
        meta={"symbol": symbol.strip().upper(), "persisted": True},
    )


@router.post("/ingest/backfill/{symbol}", response_model=ResponseEnvelope[BackfillResponseSchema])
async def backfill_historical_data(
    symbol: str,
    payload: Optional[BackfillRequestSchema] = None,
    service: MarketDataIngestionService = Depends(get_ingestion_service),
) -> ResponseEnvelope[BackfillResponseSchema]:
    """Backfill historical OHLCV bars from active provider into database."""
    req = payload or BackfillRequestSchema()
    end = req.end or datetime.now(timezone.utc)
    start = req.start or (end - timedelta(days=req.days))

    summary = await service.backfill_historical_bars(
        symbol=symbol,
        start=start,
        end=end,
        interval=req.interval,
    )
    data = BackfillResponseSchema(**summary)
    return ResponseEnvelope(
        data=data,
        meta={"start": start.isoformat(), "end": end.isoformat()},
    )


@router.post("/ingest/sync-catalog", response_model=ResponseEnvelope[SyncCatalogResponseSchema])
async def sync_catalog(
    payload: SyncCatalogRequestSchema,
    service: MarketDataIngestionService = Depends(get_ingestion_service),
) -> ResponseEnvelope[SyncCatalogResponseSchema]:
    """Search instruments via provider and sync discovered entities into database catalog."""
    instruments = await service.sync_catalog(query=payload.query)
    instrument_schemas = [
        InstrumentResponseSchema(
            symbol=inst.symbol,
            name=inst.name,
            asset_type=inst.asset.asset_class if inst.asset else "equity",
            currency=inst.currency,
            exchange=inst.exchange.code if inst.exchange else None,
            market=inst.market.name if inst.market else None,
        )
        for inst in instruments
    ]
    data = SyncCatalogResponseSchema(
        query=payload.query,
        synced_count=len(instruments),
        instruments=instrument_schemas,
    )
    return ResponseEnvelope(data=data, meta={"query": payload.query})


@router.get("/persisted-history/{symbol}", response_model=ResponseEnvelope[list[PersistedPriceSchema]])
def get_persisted_history(
    symbol: str,
    days: int = Query(default=30, ge=1, le=365, description="Number of past days to query"),
    interval: Optional[str] = Query(default="1d", description="Bar aggregation interval filter"),
    service: MarketDataIngestionService = Depends(get_ingestion_service),
) -> ResponseEnvelope[list[PersistedPriceSchema]]:
    """Retrieve persisted historical price observations directly from the database."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    prices = service.get_persisted_history(symbol=symbol, start=start, end=end, interval=interval)
    data = [
        PersistedPriceSchema(
            id=p.id,
            instrument_id=p.instrument_id,
            timestamp=p.timestamp,
            price=p.price,
            open=p.open,
            high=p.high,
            low=p.low,
            close=p.close,
            volume=p.volume,
            currency=p.currency,
            interval=p.interval,
            source=p.source,
            created_at=p.created_at,
        )
        for p in prices
    ]
    return ResponseEnvelope(
        data=data,
        meta={"symbol": symbol.strip().upper(), "count": len(data), "interval": interval},
    )
