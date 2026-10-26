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
    CacheClearResponseSchema,
    CachePurgeResponseSchema,
    CacheStatsSchema,
    CacheTTLConfigSchema,
    InstrumentResponseSchema,
    PersistedPriceSchema,
    ProviderStatusSchema,
    QuoteResponseSchema,
    SyncCatalogRequestSchema,
    SyncCatalogResponseSchema,
)
from app.core.cache import AsyncMemoryCache
from app.core.config import get_settings
from app.database.session import get_db
from app.services.ingestion import MarketDataIngestionService
from app.services.market_data import MarketDataService
from app.services.quote import QuoteService

router = APIRouter(prefix="/market-data", tags=["market-data"])

_api_cache: Optional[AsyncMemoryCache] = None


def get_api_cache() -> AsyncMemoryCache:
    """Retrieve application-level shared cache instance for API requests."""
    global _api_cache
    if _api_cache is None:
        settings = get_settings()
        _api_cache = AsyncMemoryCache(
            max_capacity=settings.cache_max_capacity,
            eviction_policy=settings.cache_eviction_policy,
        )
    return _api_cache


def get_market_data_service(
    db: Session = Depends(get_db),
    cache: AsyncMemoryCache = Depends(get_api_cache),
) -> MarketDataService:
    """Dependency injector for MarketDataService."""
    return MarketDataService(db=db, cache=cache)


def get_quote_service(service: MarketDataService = Depends(get_market_data_service)) -> QuoteService:
    """Dependency injector for QuoteService reusing MarketDataService's cached provider."""
    return service.quote_service


def get_ingestion_service(
    db: Session = Depends(get_db),
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> MarketDataIngestionService:
    """Dependency injector for MarketDataIngestionService."""
    return MarketDataIngestionService(db=db, market_data_service=market_data_service)


@router.get("/cache/stats", response_model=ResponseEnvelope[CacheStatsSchema])
async def get_cache_stats(
    service: MarketDataService = Depends(get_market_data_service),
) -> ResponseEnvelope[CacheStatsSchema]:
    """Retrieve operational metrics, hit ratios, and telemetry for the market data caching layer."""
    stats = service.get_cache_stats()
    if stats is None:
        data = CacheStatsSchema(
            enabled=False,
            size=0,
            max_capacity=0,
            eviction_policy="none",
            hits=0,
            misses=0,
            stale_hits=0,
            evictions=0,
            coalesced=0,
            hit_ratio=0.0,
            ttl_config=None,
        )
    else:
        ttl_cfg = stats.get("ttl_config")
        ttl_schema = CacheTTLConfigSchema(**ttl_cfg) if ttl_cfg else None
        data = CacheStatsSchema(
            enabled=stats["enabled"],
            size=stats["size"],
            max_capacity=stats["max_capacity"],
            eviction_policy=stats["eviction_policy"],
            hits=stats["hits"],
            misses=stats["misses"],
            stale_hits=stats.get("stale_hits", 0),
            evictions=stats["evictions"],
            coalesced=stats["coalesced"],
            hit_ratio=stats["hit_ratio"],
            ttl_config=ttl_schema,
        )
    return ResponseEnvelope(data=data)


@router.post("/cache/clear", response_model=ResponseEnvelope[CacheClearResponseSchema])
async def clear_cache(
    prefix: Optional[str] = Query(
        default=None,
        description="Optional cache key prefix to invalidate (e.g. 'quote:', 'history:', 'search:')",
    ),
    service: MarketDataService = Depends(get_market_data_service),
) -> ResponseEnvelope[CacheClearResponseSchema]:
    """Flush cached market data entries by prefix or clear the entire cache store."""
    removed = await service.clear_cache(prefix=prefix)
    data = CacheClearResponseSchema(
        cleared=True,
        prefix=prefix,
        entries_removed=removed,
    )
    return ResponseEnvelope(data=data)


@router.post("/cache/purge", response_model=ResponseEnvelope[CachePurgeResponseSchema])
async def purge_expired_cache(
    service: MarketDataService = Depends(get_market_data_service),
) -> ResponseEnvelope[CachePurgeResponseSchema]:
    """Manually sweep and purge expired entries from the market data cache store."""
    purged = await service.purge_expired_cache()
    data = CachePurgeResponseSchema(purged_count=purged)
    return ResponseEnvelope(data=data)


@router.get("/status", response_model=ResponseEnvelope[ProviderStatusSchema])
async def get_provider_status(
    service: MarketDataService = Depends(get_market_data_service),
) -> ResponseEnvelope[ProviderStatusSchema]:
    """Retrieve active market data provider health and connectivity status."""
    status = await service.get_provider_status()
    return ResponseEnvelope(data=ProviderStatusSchema(**asdict(status)))


@router.get("/quotes", response_model=ResponseEnvelope[list[QuoteResponseSchema]])
async def get_quotes(
    symbols: Optional[str] = Query(
        default=None,
        description="Comma-separated list of instrument ticker symbols (e.g. 'AAPL,MSFT,BTC-USD')",
    ),
    service: QuoteService = Depends(get_quote_service),
) -> ResponseEnvelope[list[QuoteResponseSchema]]:
    """Retrieve normalized market quotes for multiple instrument symbols in a single batch request."""
    if not symbols or not symbols.strip():
        return ResponseEnvelope(data=[], meta={"count": 0, "source": service.provider.name})

    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    quotes = await service.get_quotes(symbol_list, allow_partial=True)
    data = [QuoteResponseSchema(**asdict(q)) for q in quotes]
    return ResponseEnvelope(
        data=data,
        meta={
            "count": len(data),
            "requested": len(symbol_list),
            "source": service.provider.name,
        },
    )


@router.get("/quotes/{symbol}", response_model=ResponseEnvelope[QuoteResponseSchema])
async def get_quote(
    symbol: str,
    service: QuoteService = Depends(get_quote_service),
) -> ResponseEnvelope[QuoteResponseSchema]:
    """Retrieve normalized price quote for a given instrument symbol."""
    quote = await service.get_quote(symbol)
    return ResponseEnvelope(
        data=QuoteResponseSchema(**asdict(quote)),
        meta={
            "source": quote.data_source,
            "market_status": quote.market_status,
            "is_stale": quote.is_stale,
            "delay_minutes": quote.delay_minutes,
        },
    )


@router.get("/history/{symbol}", response_model=ResponseEnvelope[list[BarResponseSchema]])
async def get_historical_bars(
    symbol: str,
    days: Optional[int] = Query(default=None, ge=1, le=2000, description="Number of past days of history to fetch"),
    range: Optional[str] = Query(default=None, description="Timeframe range code: 1D, 1W, 1M, 3M, 6M, 1Y, 5Y, ALL"),
    interval: Optional[str] = Query(default=None, description="Bar aggregation interval (e.g. 1d, 1wk, 1mo)"),
    start: Optional[datetime] = Query(default=None, description="Explicit start datetime in ISO-8601 format"),
    end: Optional[datetime] = Query(default=None, description="Explicit end datetime in ISO-8601 format"),
    service: MarketDataService = Depends(get_market_data_service),
) -> ResponseEnvelope[list[BarResponseSchema]]:
    """Retrieve standardized and validated historical OHLCV bars for an instrument symbol."""
    series = await service.get_historical_series(
        symbol=symbol,
        range_str=range,
        days=days,
        start=start,
        end=end,
        interval=interval,
    )
    data = [BarResponseSchema(**asdict(bar)) for bar in series.bars]
    meta = {
        "symbol": series.symbol,
        "count": series.count,
        "interval": series.interval,
        "range": series.range,
        "start": series.start.isoformat(),
        "end": series.end.isoformat(),
        "source": series.data_source,
        "min_price": series.min_price,
        "max_price": series.max_price,
        "first_close": series.first_close,
        "last_close": series.last_close,
        "period_change": series.period_change,
        "period_change_percent": series.period_change_percent,
    }
    return ResponseEnvelope(data=data, meta=meta)


@router.get("/instruments", response_model=ResponseEnvelope[list[InstrumentResponseSchema]])
async def search_instruments(
    q: Optional[str] = Query(default=None, description="Search term for symbol, name, or exchange"),
    asset_type: Optional[str] = Query(default=None, description="Filter by asset class: equity, crypto, etf"),
    service: MarketDataService = Depends(get_market_data_service),
) -> ResponseEnvelope[list[InstrumentResponseSchema]]:
    """Search and filter available financial instruments."""
    clean_q = q.strip() if isinstance(q, str) else ""
    clean_type = asset_type.strip().lower() if isinstance(asset_type, str) else None
    if clean_type == "all":
        clean_type = None

    meta_q = q if isinstance(q, str) else None
    meta_type = asset_type if isinstance(asset_type, str) else None

    if not clean_q and not clean_type:
        return ResponseEnvelope(
            data=[],
            meta={"query": meta_q, "asset_type": meta_type, "count": 0},
        )

    results = await service.search_instruments(query=clean_q, asset_type=clean_type)
    data = [InstrumentResponseSchema(**asdict(item)) for item in results]
    return ResponseEnvelope(
        data=data,
        meta={"query": meta_q, "asset_type": meta_type, "count": len(data)},
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
