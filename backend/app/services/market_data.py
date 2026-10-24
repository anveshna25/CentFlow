from collections.abc import Sequence
from datetime import datetime
from typing import Optional

from app.domain.models import Instrument, Price
from app.providers.base import (
    BaseMarketDataProvider,
    ProviderBar,
    ProviderInstrument,
    ProviderQuote,
    ProviderStatus,
)
from app.providers.registry import get_provider


class MarketDataService:
    """Application service for orchestrating market data operations.

    Serves as the clean architectural boundary between API/business layers
    and external market data provider adapters.
    """

    def __init__(self, provider: Optional[BaseMarketDataProvider] = None) -> None:
        self._provider = provider or get_provider()

    @property
    def provider(self) -> BaseMarketDataProvider:
        """The active market data provider instance."""
        return self._provider

    async def get_quote(self, symbol: str) -> ProviderQuote:
        """Fetch normalized quote for an instrument symbol."""
        clean_symbol = symbol.strip().upper()
        return await self._provider.get_quote(clean_symbol)

    async def get_historical_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = "1d",
    ) -> Sequence[ProviderBar]:
        """Fetch historical price bars for an instrument symbol."""
        clean_symbol = symbol.strip().upper()
        return await self._provider.get_historical_bars(
            symbol=clean_symbol,
            start=start,
            end=end,
            interval=interval,
        )

    async def search_instruments(self, query: str) -> Sequence[ProviderInstrument]:
        """Search available instruments matching a symbol or name query."""
        if not query or not query.strip():
            return []
        return await self._provider.search_instruments(query.strip())

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
