from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from app.core.errors import InstrumentNotFoundError
from app.providers.base import (
    BaseMarketDataProvider,
    ProviderBar,
    ProviderCapabilities,
    ProviderInstrument,
    ProviderQuote,
    ProviderStatus,
)


class MockMarketDataProvider(BaseMarketDataProvider):
    """Deterministic, simulated market data provider for local development,
    offline testing, and CI validation without third-party API dependencies.
    """

    def __init__(self) -> None:
        self._simulated_error: Optional[Exception] = None
        self._capabilities = ProviderCapabilities(
            supported_intervals=("1d", "1wk", "1mo"),
            supports_search=True,
            supports_realtime=True,
            is_delayed=False,
            delay_minutes=0,
        )

    def simulate_error(self, exc: Exception) -> None:
        """Inject a simulated error for reliability and fault-tolerance testing."""
        self._simulated_error = exc

    def clear_simulated_error(self) -> None:
        """Clear any injected simulated error."""
        self._simulated_error = None

    _CATALOG: dict[str, dict] = {
        "AAPL": {
            "name": "Apple Inc.",
            "asset_type": "equity",
            "currency": "USD",
            "exchange": "NASDAQ",
            "market": "US Equities",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "price": Decimal("185.50"),
            "open": Decimal("184.20"),
            "high": Decimal("186.10"),
            "low": Decimal("183.80"),
            "previous_close": Decimal("183.90"),
            "volume": Decimal("52400000"),
        },
        "MSFT": {
            "name": "Microsoft Corporation",
            "asset_type": "equity",
            "currency": "USD",
            "exchange": "NASDAQ",
            "market": "US Equities",
            "sector": "Technology",
            "industry": "Software—Infrastructure",
            "price": Decimal("420.25"),
            "open": Decimal("418.00"),
            "high": Decimal("422.50"),
            "low": Decimal("417.10"),
            "previous_close": Decimal("416.80"),
            "volume": Decimal("21300000"),
        },
        "GOOGL": {
            "name": "Alphabet Inc.",
            "asset_type": "equity",
            "currency": "USD",
            "exchange": "NASDAQ",
            "market": "US Equities",
            "sector": "Technology",
            "industry": "Internet Content & Information",
            "price": Decimal("175.80"),
            "open": Decimal("174.50"),
            "high": Decimal("176.90"),
            "low": Decimal("174.00"),
            "previous_close": Decimal("173.60"),
            "volume": Decimal("18200000"),
        },
        "BTC-USD": {
            "name": "Bitcoin USD",
            "asset_type": "cryptocurrency",
            "currency": "USD",
            "exchange": "Coinbase",
            "market": "Crypto",
            "sector": "Cryptocurrency",
            "industry": "Digital Assets",
            "price": Decimal("65400.00"),
            "open": Decimal("64200.00"),
            "high": Decimal("66100.00"),
            "low": Decimal("63900.00"),
            "previous_close": Decimal("64150.00"),
            "volume": Decimal("28500"),
        },
        "ETH-USD": {
            "name": "Ethereum USD",
            "asset_type": "cryptocurrency",
            "currency": "USD",
            "exchange": "Coinbase",
            "market": "Crypto",
            "sector": "Cryptocurrency",
            "industry": "Digital Assets",
            "price": Decimal("3450.00"),
            "open": Decimal("3400.00"),
            "high": Decimal("3510.00"),
            "low": Decimal("3380.00"),
            "previous_close": Decimal("3390.00"),
            "volume": Decimal("192000"),
        },
        "SPY": {
            "name": "SPDR S&P 500 ETF Trust",
            "asset_type": "etf",
            "currency": "USD",
            "exchange": "NYSE",
            "market": "US ETFs",
            "price": Decimal("510.15"),
            "open": Decimal("508.40"),
            "high": Decimal("511.20"),
            "low": Decimal("507.80"),
            "previous_close": Decimal("507.60"),
            "volume": Decimal("65000000"),
        },
        "QQQ": {
            "name": "Invesco QQQ Trust (Nasdaq 100)",
            "asset_type": "etf",
            "currency": "USD",
            "exchange": "NASDAQ",
            "market": "US ETFs",
            "price": Decimal("442.80"),
            "open": Decimal("440.10"),
            "high": Decimal("444.50"),
            "low": Decimal("439.20"),
            "previous_close": Decimal("439.50"),
            "volume": Decimal("42100000"),
        },
        "NVDA": {
            "name": "NVIDIA Corporation",
            "asset_type": "equity",
            "currency": "USD",
            "exchange": "NASDAQ",
            "market": "US Equities",
            "price": Decimal("128.40"),
            "open": Decimal("126.80"),
            "high": Decimal("129.50"),
            "low": Decimal("125.90"),
            "previous_close": Decimal("125.75"),
            "volume": Decimal("78500000"),
        },
    }

    @property
    def name(self) -> str:
        return "mock"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    async def get_quote(self, symbol: str) -> ProviderQuote:
        if self._simulated_error is not None:
            raise self._simulated_error

        sym = symbol.strip().upper()
        item = self._CATALOG.get(sym)
        if not item:
            raise InstrumentNotFoundError(symbol=sym)

        price = item["price"]
        prev_close = item["previous_close"]
        change = price - prev_close
        change_pct = (change / prev_close) * Decimal("100")

        return ProviderQuote(
            symbol=sym,
            price=price,
            currency=item["currency"],
            timestamp=datetime.now(timezone.utc),
            volume=item["volume"],
            open=item["open"],
            high=item["high"],
            low=item["low"],
            previous_close=prev_close,
            change=change.quantize(Decimal("0.01")),
            change_percent=change_pct.quantize(Decimal("0.01")),
        )

    async def get_historical_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = "1d",
    ) -> Sequence[ProviderBar]:
        if self._simulated_error is not None:
            raise self._simulated_error

        sym = symbol.strip().upper()
        item = self._CATALOG.get(sym)
        if not item:
            raise InstrumentNotFoundError(symbol=sym)

        bars: list[ProviderBar] = []
        base_price = item["price"]
        current = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = end.replace(hour=0, minute=0, second=0, microsecond=0)

        if interval in ("1wk", "1w", "1WK", "1W"):
            step = timedelta(weeks=1)
        elif interval in ("1mo", "1m", "1MO", "1M"):
            step = timedelta(days=30)
        elif interval in ("1h", "1H"):
            step = timedelta(hours=1)
        elif interval in ("15m", "15M"):
            step = timedelta(minutes=15)
        elif interval in ("5m", "5M"):
            step = timedelta(minutes=5)
        else:
            step = timedelta(days=1)

        day_index = 0

        while current <= end_date:
            # Deterministic variation using day index
            offset = Decimal((day_index % 7) - 3) * Decimal("0.75")
            bar_open = (base_price + offset).quantize(Decimal("0.01"))
            bar_close = (bar_open + Decimal("0.50")).quantize(Decimal("0.01"))
            bar_high = max(bar_open, bar_close) + Decimal("1.20")
            bar_low = min(bar_open, bar_close) - Decimal("1.10")
            bar_volume = (item["volume"] * Decimal("0.9")).quantize(Decimal("1"))

            bars.append(
                ProviderBar(
                    symbol=sym,
                    timestamp=current,
                    open=bar_open,
                    high=bar_high,
                    low=bar_low,
                    close=bar_close,
                    volume=bar_volume,
                )
            )
            current += step
            day_index += 1

        return bars

    async def search_instruments(
        self,
        query: str = "",
        asset_type: Optional[str] = None,
    ) -> Sequence[ProviderInstrument]:
        if self._simulated_error is not None:
            raise self._simulated_error

        q = (query or "").strip().lower()
        clean_type = (asset_type or "").strip().lower()
        if clean_type == "all":
            clean_type = ""

        if not q and not clean_type:
            return []

        if clean_type in ("cryptocurrency", "crypto"):
            target_types = {"crypto", "cryptocurrency"}
        elif clean_type:
            target_types = {clean_type}
        else:
            target_types = None

        results: list[ProviderInstrument] = []
        for sym, item in self._CATALOG.items():
            raw_type = item.get("asset_type", "equity").lower()
            norm_type = "crypto" if raw_type in ("crypto", "cryptocurrency") else raw_type

            if target_types is not None and raw_type not in target_types and norm_type not in target_types:
                continue

            if not q or (
                q in sym.lower()
                or q in item["name"].lower()
                or (item.get("exchange") and q in item["exchange"].lower())
                or (item.get("sector") and q in item["sector"].lower())
            ):
                results.append(
                    ProviderInstrument(
                        symbol=sym,
                        name=item["name"],
                        asset_type=norm_type,
                        currency=item["currency"],
                        exchange=item.get("exchange"),
                        market=item.get("market"),
                        country="US" if item.get("exchange") in ("NASDAQ", "NYSE") else "Global",
                        sector=item.get("sector"),
                        industry=item.get("industry"),
                    )
                )
        return results

    async def lookup_asset(self, symbol: str) -> Optional[ProviderInstrument]:
        if self._simulated_error is not None:
            raise self._simulated_error

        sym = symbol.strip().upper()
        item = self._CATALOG.get(sym)
        if not item:
            return None

        return ProviderInstrument(
            symbol=sym,
            name=item["name"],
            asset_type=item["asset_type"],
            currency=item["currency"],
            exchange=item.get("exchange"),
            market=item.get("market"),
            country="US" if item.get("exchange") in ("NASDAQ", "NYSE") else "Global",
            sector=item.get("sector"),
            industry=item.get("industry"),
        )

    async def get_status(self) -> ProviderStatus:
        if self._simulated_error is not None:
            raise self._simulated_error

        return ProviderStatus(
            name=self.name,
            is_active=True,
            message="Deterministic mock market data provider operational.",
            latency_ms=0.1,
            capabilities=self.capabilities,
        )
