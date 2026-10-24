import unittest
from app.api.routes.market_data import (
    get_historical_bars,
    get_market_data_service,
    get_provider_status,
    get_quote,
    search_instruments,
)
from app.api.schemas.base import ResponseEnvelope
from app.core.errors import InstrumentNotFoundError
from app.main import create_app


class TestMarketDataApiRoutes(unittest.IsolatedAsyncioTestCase):
    """Test market data API route handlers and envelope responses."""

    async def asyncSetUp(self):
        self.service = get_market_data_service()

    async def test_get_provider_status_route(self):
        envelope = await get_provider_status(service=self.service)
        self.assertIsInstance(envelope, ResponseEnvelope)
        self.assertEqual(envelope.data.name, "mock")
        self.assertTrue(envelope.data.is_active)

    async def test_get_quote_route_success(self):
        envelope = await get_quote(symbol="AAPL", service=self.service)
        self.assertIsInstance(envelope, ResponseEnvelope)
        self.assertEqual(envelope.data.symbol, "AAPL")
        self.assertEqual(envelope.data.currency, "USD")
        self.assertEqual(envelope.meta["source"], "mock")

    async def test_get_quote_route_not_found(self):
        with self.assertRaises(InstrumentNotFoundError):
            await get_quote(symbol="UNKNOWN_SYM", service=self.service)

    async def test_get_historical_bars_route(self):
        envelope = await get_historical_bars(symbol="MSFT", days=5, interval="1d", service=self.service)
        self.assertIsInstance(envelope, ResponseEnvelope)
        self.assertGreaterEqual(len(envelope.data), 5)
        self.assertEqual(envelope.meta["source"], "mock")
        self.assertEqual(envelope.meta["interval"], "1d")

    async def test_search_instruments_route(self):
        envelope = await search_instruments(q="Bitcoin", service=self.service)
        self.assertIsInstance(envelope, ResponseEnvelope)
        self.assertTrue(any(item.symbol == "BTC-USD" for item in envelope.data))
        self.assertEqual(envelope.meta["query"], "Bitcoin")


class TestAppCorsConfiguration(unittest.TestCase):
    """Test CORS middleware presence and configuration in create_app."""

    def test_app_factory_includes_cors_middleware(self):
        app = create_app()
        # Find CORSMiddleware in middleware stack
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        self.assertIn("CORSMiddleware", middleware_classes)


if __name__ == "__main__":
    unittest.main()
