from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.core.errors import InstrumentNotFoundError
from app.providers.base import (
    BaseMarketDataProvider,
    ProviderBar,
    ProviderInstrument,
    ProviderQuote,
    ProviderStatus,
)


class MockMarketDataProvider(BaseMarketDataProvider):
    """Deterministic, simulated market data provider for local development,
    offline testing, and CI validation without third-party API dependencies.
    """

    _CATALOG: dict[str, dict] = {
        "AAPL": {
            "name": "Apple Inc.",
            "asset_type": "equity",
            "currency": "USD",
            "exchange": "NASDAQ",
            "market": "US Equities",
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

    async def get_quote(self, symbol: str) -> ProviderQuote:
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
        sym = symbol.strip().upper()
        item = self._CATALOG.get(sym)
        if not item:
            raise InstrumentNotFoundError(symbol=sym)

        bars: list[ProviderBar] = []
        base_price = item["price"]
        current = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = end.replace(hour=0, minute=0, second=0, microsecond=0)

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

    async def search_instruments(self, query: str) -> Sequence[ProviderInstrument]:
        q = query.strip().lower()
        if not q:
            return []

        results: list[ProviderInstrument] = []
        for sym, item in self._CATALOG.items():
            if q in sym.lower() or q in item["name"].lower():
                results.append(
                    ProviderInstrument(
                        symbol=sym,
                        name=item["name"],
                        asset_type=item["asset_type"],
                        currency=item["currency"],
                        exchange=item.get("exchange"),
                        market=item.get("market"),
                    )
                )
        return results

    async def get_status(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            is_active=True,
            message="Deterministic mock market data provider operational.",
        )
