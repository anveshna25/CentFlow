import unittest
from fastapi.testclient import TestClient

from app.main import create_app


class TestQuoteApiEndpoints(unittest.TestCase):
    """Test suite executing HTTP requests against FastAPI quote endpoints via TestClient."""

    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_get_single_quote_success(self):
        """GET /api/v1/market-data/quotes/AAPL returns 200 with enriched quote data."""
        response = self.client.get("/api/v1/market-data/quotes/AAPL")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("data", payload)
        self.assertIn("meta", payload)

        data = payload["data"]
        self.assertEqual(data["symbol"], "AAPL")
        self.assertEqual(data["currency"], "USD")
        self.assertGreater(float(data["price"]), 0)
        self.assertIn("market_status", data)
        self.assertIn("is_stale", data)
        self.assertIn("delay_minutes", data)
        self.assertIn("data_source", data)

        meta = payload["meta"]
        self.assertEqual(meta["source"], "mock")
        self.assertIn("market_status", meta)
        self.assertIn("is_stale", meta)

    def test_get_single_quote_crypto(self):
        """GET /api/v1/market-data/quotes/BTC-USD returns 200 with market_status OPEN."""
        response = self.client.get("/api/v1/market-data/quotes/BTC-USD")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        data = payload["data"]
        self.assertEqual(data["symbol"], "BTC-USD")
        self.assertEqual(data["market_status"], "OPEN")

    def test_get_single_quote_not_found(self):
        """GET /api/v1/market-data/quotes/NONEXISTENT returns 404 with error envelope."""
        response = self.client.get("/api/v1/market-data/quotes/NONEXISTENT")
        self.assertEqual(response.status_code, 404)
        payload = response.json()
        self.assertIn("error", payload)
        self.assertEqual(payload["error"]["code"], "RESOURCE_NOT_FOUND")

    def test_get_batch_quotes_success(self):
        """GET /api/v1/market-data/quotes?symbols=AAPL,MSFT,BTC-USD returns 200 with list."""
        response = self.client.get("/api/v1/market-data/quotes?symbols=AAPL,MSFT,BTC-USD")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("data", payload)
        self.assertIn("meta", payload)
        self.assertEqual(len(payload["data"]), 3)
        self.assertEqual(payload["meta"]["count"], 3)
        self.assertEqual(payload["meta"]["requested"], 3)

        symbols = [item["symbol"] for item in payload["data"]]
        self.assertEqual(symbols, ["AAPL", "MSFT", "BTC-USD"])

    def test_get_batch_quotes_empty(self):
        """GET /api/v1/market-data/quotes without symbols returns 200 with empty list."""
        response = self.client.get("/api/v1/market-data/quotes")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data"], [])
        self.assertEqual(payload["meta"]["count"], 0)

    def test_get_batch_quotes_partial_success(self):
        """GET /api/v1/market-data/quotes?symbols=AAPL,NONEXISTENT returns valid quotes."""
        response = self.client.get("/api/v1/market-data/quotes?symbols=AAPL,NONEXISTENT")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["data"]), 1)
        self.assertEqual(payload["data"][0]["symbol"], "AAPL")
        self.assertEqual(payload["meta"]["count"], 1)
        self.assertEqual(payload["meta"]["requested"], 2)


if __name__ == "__main__":
    unittest.main()
