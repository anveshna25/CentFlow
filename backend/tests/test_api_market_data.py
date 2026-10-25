import unittest
from fastapi.testclient import TestClient

from app.api.routes.market_data import search_instruments
from app.api.schemas.base import ResponseEnvelope
from app.main import create_app
from app.services.market_data import MarketDataService


class TestMarketDataSearchRoute(unittest.IsolatedAsyncioTestCase):
    """Test suite covering Market Data search route and ResponseEnvelope integration."""

    async def asyncSetUp(self):
        self.service = MarketDataService(enable_cache=False)

    async def test_search_instruments_route_handler_match(self):
        """search_instruments route should return matching instruments wrapped in ResponseEnvelope."""
        envelope = await search_instruments(q="AAPL", service=self.service)
        self.assertIsInstance(envelope, ResponseEnvelope)
        self.assertGreaterEqual(len(envelope.data), 1)
        self.assertEqual(envelope.data[0].symbol, "AAPL")
        self.assertEqual(envelope.data[0].asset_type, "equity")
        self.assertEqual(envelope.meta["query"], "AAPL")
        self.assertGreaterEqual(envelope.meta["count"], 1)

    async def test_search_instruments_route_handler_empty(self):
        """Empty query should return empty data list with count 0."""
        envelope = await search_instruments(q="", service=self.service)
        self.assertIsInstance(envelope, ResponseEnvelope)
        self.assertEqual(len(envelope.data), 0)
        self.assertEqual(envelope.meta["count"], 0)


class TestMarketDataHttpEndpoints(unittest.TestCase):
    """Integration test suite executing HTTP requests against FastAPI app via TestClient."""

    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_http_search_instruments_success(self):
        """GET /api/v1/market-data/instruments?q=... returns 200 with matching catalog."""
        response = self.client.get("/api/v1/market-data/instruments?q=AAPL")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("data", payload)
        self.assertIn("meta", payload)
        self.assertGreaterEqual(len(payload["data"]), 1)
        self.assertEqual(payload["data"][0]["symbol"], "AAPL")
        self.assertEqual(payload["meta"]["query"], "AAPL")

    def test_http_search_instruments_crypto(self):
        """GET /api/v1/market-data/instruments?q=Bitcoin finds BTC-USD crypto instrument."""
        response = self.client.get("/api/v1/market-data/instruments?q=Bitcoin")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(len(payload["data"]), 1)
        symbols = [item["symbol"] for item in payload["data"]]
        self.assertIn("BTC-USD", symbols)

    def test_http_search_instruments_empty_query(self):
        """GET /api/v1/market-data/instruments without query returns empty array."""
        response = self.client.get("/api/v1/market-data/instruments")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data"], [])
        self.assertEqual(payload["meta"]["count"], 0)


if __name__ == "__main__":
    unittest.main()
