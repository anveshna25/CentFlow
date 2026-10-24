import unittest
from datetime import datetime, timezone
from decimal import Decimal

from app.core.errors import CentFlowException, InstrumentNotFoundError
from app.domain.models import Asset, Instrument
from app.providers.base import (
    BaseMarketDataProvider,
    ProviderBar,
    ProviderInstrument,
    ProviderQuote,
    ProviderStatus,
)
from app.providers.mock import MockMarketDataProvider
from app.providers.registry import ProviderRegistry, get_provider
from app.services.market_data import MarketDataService


class TestMockMarketDataProvider(unittest.IsolatedAsyncioTestCase):
    """Test the deterministic mock market data provider."""

    async def asyncSetUp(self):
        self.provider = MockMarketDataProvider()

    async def test_provider_name_and_status(self):
        self.assertEqual(self.provider.name, "mock")
        status = await self.provider.get_status()
        self.assertEqual(status.name, "mock")
        self.assertTrue(status.is_active)
        self.assertIn("operational", status.message.lower())

    async def test_get_quote_valid_symbol(self):
        quote = await self.provider.get_quote("AAPL")
        self.assertIsInstance(quote, ProviderQuote)
        self.assertEqual(quote.symbol, "AAPL")
        self.assertEqual(quote.currency, "USD")
        self.assertGreater(quote.price, Decimal("0"))
        self.assertIsNotNone(quote.timestamp)
        self.assertIsNotNone(quote.volume)
        self.assertIsNotNone(quote.open)
        self.assertIsNotNone(quote.high)
        self.assertIsNotNone(quote.low)
        self.assertIsNotNone(quote.change)
        self.assertIsNotNone(quote.change_percent)

    async def test_get_quote_case_insensitive_and_whitespace(self):
        quote = await self.provider.get_quote("  aapl  ")
        self.assertEqual(quote.symbol, "AAPL")

    async def test_get_quote_unknown_symbol_raises_not_found(self):
        with self.assertRaises(InstrumentNotFoundError):
            await self.provider.get_quote("NONEXISTENT_XYZ")

    async def test_get_historical_bars(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 5, tzinfo=timezone.utc)
        bars = await self.provider.get_historical_bars("AAPL", start=start, end=end)

        self.assertEqual(len(bars), 5)
        for bar in bars:
            self.assertIsInstance(bar, ProviderBar)
            self.assertEqual(bar.symbol, "AAPL")
            self.assertGreater(bar.high, Decimal("0"))
            self.assertLessEqual(bar.low, bar.high)
            self.assertGreaterEqual(bar.volume, Decimal("0"))

    async def test_get_historical_bars_unknown_symbol_raises(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 3, tzinfo=timezone.utc)
        with self.assertRaises(InstrumentNotFoundError):
            await self.provider.get_historical_bars("INVALID_SYM", start, end)

    async def test_search_instruments(self):
        results = await self.provider.search_instruments("apple")
        self.assertTrue(any(r.symbol == "AAPL" for r in results))

        crypto_results = await self.provider.search_instruments("bitcoin")
        self.assertTrue(any(r.symbol == "BTC-USD" for r in crypto_results))

    async def test_search_instruments_empty_query(self):
        results = await self.provider.search_instruments("")
        self.assertEqual(results, [])


class TestProviderRegistry(unittest.TestCase):
    """Test provider registry and factory mechanisms."""

    def setUp(self):
        ProviderRegistry.clear()
        ProviderRegistry.register("mock", MockMarketDataProvider)

    def tearDown(self):
        ProviderRegistry.clear()

    def test_get_default_provider(self):
        provider = ProviderRegistry.get("mock")
        self.assertIsInstance(provider, MockMarketDataProvider)
        self.assertEqual(provider.name, "mock")

    def test_get_provider_helper(self):
        provider = get_provider("mock")
        self.assertIsInstance(provider, MockMarketDataProvider)

    def test_custom_provider_registration(self):
        class DummyProvider(BaseMarketDataProvider):
            @property
            def name(self) -> str:
                return "dummy"

            async def get_quote(self, symbol: str) -> ProviderQuote:
                pass

            async def get_historical_bars(self, symbol: str, start: datetime, end: datetime, interval: str = "1d"):
                pass

            async def search_instruments(self, query: str):
                pass

            async def get_status(self) -> ProviderStatus:
                pass

        ProviderRegistry.register("dummy", DummyProvider)
        provider = ProviderRegistry.get("dummy")
        self.assertIsInstance(provider, DummyProvider)
        self.assertEqual(provider.name, "dummy")

    def test_unregistered_provider_raises(self):
        with self.assertRaises(CentFlowException) as ctx:
            ProviderRegistry.get("unregistered_vendor")
        self.assertIn("not registered", ctx.exception.message)


class TestMarketDataService(unittest.IsolatedAsyncioTestCase):
    """Test MarketDataService orchestration and domain conversions."""

    async def asyncSetUp(self):
        self.mock_provider = MockMarketDataProvider()
        self.service = MarketDataService(provider=self.mock_provider)

    async def test_service_delegates_quote(self):
        quote = await self.service.get_quote("MSFT")
        self.assertEqual(quote.symbol, "MSFT")
        self.assertEqual(quote.currency, "USD")

    async def test_service_delegates_historical_bars(self):
        start = datetime(2026, 3, 1, tzinfo=timezone.utc)
        end = datetime(2026, 3, 3, tzinfo=timezone.utc)
        bars = await self.service.get_historical_bars("MSFT", start, end)
        self.assertEqual(len(bars), 3)

    async def test_service_delegates_search(self):
        results = await self.service.search_instruments("micro")
        self.assertTrue(any(r.symbol == "MSFT" for r in results))

    async def test_service_empty_search_returns_empty_list(self):
        results = await self.service.search_instruments("   ")
        self.assertEqual(results, [])

    async def test_service_status(self):
        status = await self.service.get_provider_status()
        self.assertEqual(status.name, "mock")
        self.assertTrue(status.is_active)

    def test_to_domain_price_conversion(self):
        quote = ProviderQuote(
            symbol="AAPL",
            price=Decimal("185.50"),
            currency="USD",
            timestamp=datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc),
        )
        instrument = Instrument(
            id="inst_1",
            symbol="AAPL",
            name="Apple Inc.",
            asset=Asset(id="asset_1", name="Apple Inc.", asset_type="equity"),
        )

        price_model = MarketDataService.to_domain_price(quote, instrument)
        self.assertEqual(price_model.instrument.symbol, "AAPL")
        self.assertEqual(price_model.value, Decimal("185.50"))
        self.assertEqual(price_model.currency, "USD")
        self.assertEqual(price_model.timestamp, quote.timestamp)


if __name__ == "__main__":
    unittest.main()
