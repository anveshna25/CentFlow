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

    async def test_search_instruments_with_asset_type_filter(self):
        """search_instruments with asset_type returns only matching asset class items."""
        envelope = await search_instruments(q=None, asset_type="crypto", service=self.service)
        self.assertIsInstance(envelope, ResponseEnvelope)
        self.assertGreaterEqual(len(envelope.data), 1)
        for item in envelope.data:
            self.assertEqual(item.asset_type, "crypto")
        self.assertEqual(envelope.meta["asset_type"], "crypto")

    async def test_search_instruments_with_both_query_and_asset_type(self):
        """search_instruments with query and asset_type applies both filters."""
        envelope = await search_instruments(q="AAPL", asset_type="equity", service=self.service)
        self.assertEqual(len(envelope.data), 1)
        self.assertEqual(envelope.data[0].symbol, "AAPL")
        self.assertEqual(envelope.data[0].asset_type, "equity")

        mismatch = await search_instruments(q="AAPL", asset_type="crypto", service=self.service)
        self.assertEqual(len(mismatch.data), 0)
        self.assertEqual(mismatch.meta["count"], 0)


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

    def test_http_search_instruments_by_asset_type_crypto(self):
        """GET /api/v1/market-data/instruments?asset_type=crypto returns only cryptocurrencies."""
        response = self.client.get("/api/v1/market-data/instruments?asset_type=crypto")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(len(payload["data"]), 2)
        symbols = {item["symbol"] for item in payload["data"]}
        self.assertIn("BTC-USD", symbols)
        self.assertIn("ETH-USD", symbols)
        for item in payload["data"]:
            self.assertEqual(item["asset_type"], "crypto")

    def test_http_search_instruments_by_asset_type_etf(self):
        """GET /api/v1/market-data/instruments?asset_type=etf returns ETF instruments."""
        response = self.client.get("/api/v1/market-data/instruments?asset_type=etf")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(len(payload["data"]), 2)
        symbols = {item["symbol"] for item in payload["data"]}
        self.assertIn("SPY", symbols)
        self.assertIn("QQQ", symbols)

    def test_http_search_instruments_compound_query_match(self):
        """GET /api/v1/market-data/instruments?q=SPY&asset_type=etf matches SPDR S&P 500 ETF."""
        response = self.client.get("/api/v1/market-data/instruments?q=SPY&asset_type=etf")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["data"]), 1)
        self.assertEqual(payload["data"][0]["symbol"], "SPY")

    def test_http_search_instruments_compound_query_mismatch_returns_empty(self):
        """GET /api/v1/market-data/instruments?q=SPY&asset_type=crypto returns empty array."""
        response = self.client.get("/api/v1/market-data/instruments?q=SPY&asset_type=crypto")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data"], [])
        self.assertEqual(payload["meta"]["count"], 0)

    def test_http_search_instruments_empty_state_on_nonexistent(self):
        """GET /api/v1/market-data/instruments?q=NO_SUCH_TICKER_999 returns empty list."""
        response = self.client.get("/api/v1/market-data/instruments?q=NO_SUCH_TICKER_999")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data"], [])
        self.assertEqual(payload["meta"]["count"], 0)


if __name__ == "__main__":
    unittest.main()
