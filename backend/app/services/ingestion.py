from collections.abc import Sequence
from datetime import datetime
from typing import Any, Optional
from sqlalchemy.orm import Session
from app.core.errors import InstrumentNotFoundError
from app.database.models.instrument import InstrumentModel
from app.database.models.price import PriceModel
from app.providers.base import ProviderInstrument
from app.repositories.asset import AssetRepository
from app.repositories.instrument import InstrumentRepository
from app.repositories.price import PriceRepository
from app.services.market_data import MarketDataService


class MarketDataIngestionService:
    """Service orchestrating market data ingestion, synchronization, and persistent backfills.

    Bridges provider queries with repository persistence routines, ensuring instruments,
    real-time price observations, and historical OHLCV bars are durably recorded in
    the relational database.
    """

    def __init__(
        self,
        db: Session,
        market_data_service: Optional[MarketDataService] = None,
    ) -> None:
        self.db = db
        self.market_data_service = market_data_service or MarketDataService()
        self.instrument_repo = InstrumentRepository(db)
        self.price_repo = PriceRepository(db)
        self.asset_repo = AssetRepository(db)

    async def ensure_instrument(self, symbol: str) -> InstrumentModel:
        """Locate an instrument by symbol in the database or discover and persist it."""
        clean_symbol = symbol.strip().upper()
        existing = self.instrument_repo.get_by_symbol(clean_symbol)
        if existing:
            return existing

        # First try search via market data provider
        search_results = await self.market_data_service.search_instruments(clean_symbol)
        matching = next(
            (item for item in search_results if item.symbol.strip().upper() == clean_symbol),
            None,
        )
        if matching:
            return self.instrument_repo.get_or_create_from_provider(matching)

        # Fallback to fetching live quote to verify validity
        try:
            quote = await self.market_data_service.get_quote(clean_symbol)
            fallback_item = ProviderInstrument(
                symbol=clean_symbol,
                name=clean_symbol,
                asset_type="equity",
                currency=quote.currency,
            )
            return self.instrument_repo.get_or_create_from_provider(fallback_item)
        except Exception:
            raise InstrumentNotFoundError(symbol=clean_symbol)

    async def ingest_quote(self, symbol: str, interval: str = "tick") -> PriceModel:
        """Fetch and persist the latest quote observation for an instrument."""
        clean_symbol = symbol.strip().upper()
        instrument = await self.ensure_instrument(clean_symbol)
        quote = await self.market_data_service.get_quote(clean_symbol)
        source = self.market_data_service.provider.name

        return self.price_repo.insert_quote_observation(
            instrument_id=instrument.id,
            quote=quote,
            interval=interval,
            source=source,
        )

    async def backfill_historical_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = "1d",
    ) -> dict[str, Any]:
        """Fetch and bulk-persist historical OHLCV bars for an instrument."""
        clean_symbol = symbol.strip().upper()
        instrument = await self.ensure_instrument(clean_symbol)
        bars = await self.market_data_service.get_historical_bars(
            symbol=clean_symbol,
            start=start,
            end=end,
            interval=interval,
        )
        source = self.market_data_service.provider.name

        count = self.price_repo.bulk_insert_bars(
            instrument_id=instrument.id,
            bars=bars,
            currency=instrument.currency,
            interval=interval,
            source=source,
        )

        return {
            "symbol": clean_symbol,
            "instrument_id": instrument.id,
            "bars_ingested": count,
            "interval": interval,
            "source": source,
        }

    async def sync_catalog(self, query: str) -> Sequence[InstrumentModel]:
        """Search instruments from provider and persist discovered catalog items."""
        results = await self.market_data_service.search_instruments(query)
        synced: list[InstrumentModel] = []
        for item in results:
            inst = self.instrument_repo.get_or_create_from_provider(item)
            synced.append(inst)
        return synced

    def get_persisted_history(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        interval: Optional[str] = None,
    ) -> Sequence[PriceModel]:
        """Query stored price history from the database."""
        clean_symbol = symbol.strip().upper()
        instrument = self.instrument_repo.get_by_symbol(clean_symbol)
        if not instrument:
            return []
        return self.price_repo.get_historical_prices(
            instrument_id=instrument.id,
            start=start,
            end=end,
            interval=interval,
        )
