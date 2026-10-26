from collections.abc import Sequence
from datetime import datetime
from typing import Any, Optional

from app.core.config import get_settings
from app.domain.models import Instrument, Price
from app.providers.base import (
    BaseMarketDataProvider,
    ProviderBar,
    ProviderInstrument,
    ProviderQuote,
    ProviderStatus,
)
from app.providers.cache import CachedMarketDataProvider
from app.providers.registry import get_provider


from app.services.history import HistoricalSeries, HistoryService
from app.services.quote import MarketQuote, QuoteService


class MarketDataService:
    """Application service for orchestrating market data operations.

    Serves as the clean architectural boundary between API/business layers
    and external market data provider adapters, incorporating caching
    and rate-limiting layers.
    """

    def __init__(
        self,
        provider: Optional[BaseMarketDataProvider] = None,
        enable_cache: Optional[bool] = None,
        db: Optional[Any] = None,
        cache: Optional[Any] = None,
    ) -> None:
        raw_provider = provider or get_provider()
        settings = get_settings()
        should_cache = enable_cache if enable_cache is not None else settings.market_data_cache_enabled

        if should_cache and not isinstance(raw_provider, CachedMarketDataProvider):
            db_fallback_fn = self._create_db_quote_fallback(db) if db is not None else None
            db_history_fallback_fn = self._create_db_history_fallback(db) if db is not None else None
            self._provider = CachedMarketDataProvider(
                provider=raw_provider,
                quote_ttl=settings.quote_cache_ttl_seconds,
                history_ttl=settings.history_cache_ttl_seconds,
                search_ttl=settings.search_cache_ttl_seconds,
                asset_ttl=settings.asset_cache_ttl_seconds,
                stale_grace_ttl=settings.cache_stale_grace_seconds,
                cache=cache,
                max_capacity=settings.cache_max_capacity,
                eviction_policy=settings.cache_eviction_policy,
                enabled=True,
                db_fallback_fn=db_fallback_fn,
                db_history_fallback_fn=db_history_fallback_fn,
            )
        else:
            self._provider = raw_provider

        self._db = db
        self._quote_service = QuoteService(provider=self._provider, enable_cache=False)
        self._history_service = HistoryService(provider=self._provider)

    def _create_db_quote_fallback(self, db: Any):
        """Build persistence fallback lookup for live quotes when provider is down."""
        from app.repositories.instrument import InstrumentRepository
        from app.repositories.price import PriceRepository

        def fallback(symbol: str) -> Optional[ProviderQuote]:
            inst_repo = InstrumentRepository(db)
            inst = inst_repo.get_by_symbol(symbol)
            if inst is None:
                return None
            price_repo = PriceRepository(db)
            latest = price_repo.get_latest_price(inst.id)
            if latest is None:
                return None
            return ProviderQuote(
                symbol=inst.symbol,
                price=latest.price,
                currency=latest.currency,
                timestamp=latest.timestamp,
                volume=latest.volume,
                open=latest.open,
                high=latest.high,
                low=latest.low,
                previous_close=None,
                change=None,
                change_percent=None,
                is_stale=True,
            )

        return fallback

    def _create_db_history_fallback(self, db: Any):
        """Build persistence fallback lookup for historical bars when provider is down."""
        from decimal import Decimal
        from app.repositories.instrument import InstrumentRepository
        from app.repositories.price import PriceRepository

        def fallback(symbol: str, start: datetime, end: datetime, interval: str) -> Sequence[ProviderBar]:
            inst_repo = InstrumentRepository(db)
            inst = inst_repo.get_by_symbol(symbol)
            if inst is None:
                return []
            price_repo = PriceRepository(db)
            prices = price_repo.get_historical_prices(inst.id, start=start, end=end, interval=interval)
            return [
                ProviderBar(
                    symbol=inst.symbol,
                    timestamp=p.timestamp,
                    open=p.open or p.price,
                    high=p.high or p.price,
                    low=p.low or p.price,
                    close=p.close or p.price,
                    volume=p.volume or Decimal("0"),
                )
                for p in prices
            ]

        return fallback

    @property
    def provider(self) -> BaseMarketDataProvider:
        """The active market data provider instance."""
        return self._provider

    @property
    def quote_service(self) -> QuoteService:
        """The dedicated QuoteService instance."""
        return self._quote_service

    @property
    def history_service(self) -> HistoryService:
        """The dedicated HistoryService instance."""
        return self._history_service

    @property
    def capabilities(self):
        """Operational capabilities declared by active market data provider."""
        return self._provider.capabilities

    async def close(self) -> None:
        """Close provider resources."""
        await self._provider.close()

    def get_cache_stats(self) -> Optional[dict[str, Any]]:
        """Retrieve cache performance statistics if caching layer is active."""
        if isinstance(self._provider, CachedMarketDataProvider):
            return self._provider.get_stats()
        return None

    async def clear_cache(self, prefix: Optional[str] = None) -> int:
        """Clear cache entries matching prefix, or all entries if prefix is None.

        Returns:
            Count of removed entries.
        """
        if isinstance(self._provider, CachedMarketDataProvider):
            return await self._provider.clear_cache(prefix=prefix)
        return 0

    async def purge_expired_cache(self) -> int:
        """Purge expired cache entries from memory store.

        Returns:
            Count of removed entries.
        """
        if isinstance(self._provider, CachedMarketDataProvider):
            return await self._provider.purge_expired()
        return 0

    async def get_quote(self, symbol: str) -> MarketQuote:
        """Fetch normalized, validated quote for an instrument symbol."""
        return await self._quote_service.get_quote(symbol)

    async def get_quotes(
        self,
        symbols: Sequence[str],
        allow_partial: bool = True,
    ) -> list[MarketQuote]:
        """Fetch batch of normalized, validated quotes for multiple instrument symbols."""
        return await self._quote_service.get_quotes(symbols, allow_partial=allow_partial)

    async def get_historical_bars(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        interval: str = "1d",
        range: Optional[str] = None,
        days: Optional[int] = None,
    ) -> Sequence[ProviderBar]:
        """Fetch historical price bars for an instrument symbol."""
        series = await self._history_service.get_historical_series(
            symbol=symbol,
            range_str=range,
            days=days,
            start=start,
            end=end,
            interval=interval,
        )
        return series.bars

    async def get_historical_series(
        self,
        symbol: str,
        range_str: Optional[str] = None,
        days: Optional[int] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        interval: Optional[str] = None,
    ) -> HistoricalSeries:
        """Fetch full historical series with validation and summary metrics."""
        return await self._history_service.get_historical_series(
            symbol=symbol,
            range_str=range_str,
            days=days,
            start=start,
            end=end,
            interval=interval,
        )

    async def search_instruments(
        self,
        query: str = "",
        asset_type: Optional[str] = None,
    ) -> Sequence[ProviderInstrument]:
        """Search available instruments matching a symbol, name, or asset type query."""
        clean_q = (query or "").strip()
        clean_type = (asset_type or "").strip().lower() if asset_type else None
        if clean_type == "all":
            clean_type = None

        if not clean_q and not clean_type:
            return []

        results: list[ProviderInstrument] = []
        try:
            provider_results = await self._provider.search_instruments(clean_q, asset_type=clean_type)
            results.extend(provider_results)
        except Exception:
            pass

        # Fallback to local instrument catalog in database if provider yielded no results and db is present
        if not results and self._db is not None:
            try:
                from app.repositories.instrument import InstrumentRepository
                inst_repo = InstrumentRepository(self._db)
                if clean_q:
                    db_instruments = inst_repo.search(clean_q, limit=50)
                else:
                    db_instruments = inst_repo.list_with_relations(active_only=True, limit=50)

                for inst in db_instruments:
                    inst_type = inst.asset.asset_class.lower() if inst.asset else "equity"
                    if clean_type and inst_type != clean_type:
                        continue
                    results.append(
                        ProviderInstrument(
                            symbol=inst.symbol,
                            name=inst.name,
                            asset_type=inst_type,
                            currency=inst.currency,
                            exchange=inst.exchange.code if inst.exchange else None,
                            market=inst.market.name if inst.market else None,
                        )
                    )
            except Exception:
                pass

        # Deduplicate while preserving order
        seen: set[str] = set()
        deduped: list[ProviderInstrument] = []
        for item in results:
            sym_key = item.symbol.strip().upper()
            if sym_key not in seen:
                seen.add(sym_key)
                deduped.append(item)

        return deduped

    async def lookup_asset(self, symbol: str) -> Optional[ProviderInstrument]:
        """Fetch canonical instrument record for a specific symbol directly from provider."""
        if not symbol or not symbol.strip():
            return None
        return await self._provider.lookup_asset(symbol.strip().upper())

    async def get_provider_status(self) -> ProviderStatus:
        """Check provider connectivity and operational status."""
        return await self._provider.get_status()

    @staticmethod
    def to_domain_price(quote: ProviderQuote, instrument: Instrument) -> Price:
        """Convert a normalized ProviderQuote into a core CentFlow domain Price model."""
        return Price(
            instrument=instrument,
            value=quote.price,
            currency=quote.currency,
            timestamp=quote.timestamp,
        )
