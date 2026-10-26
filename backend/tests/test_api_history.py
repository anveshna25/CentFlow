"""Test suite executing HTTP requests against FastAPI historical market data endpoints via TestClient."""

from datetime import datetime, timezone
import unittest
from fastapi.testclient import TestClient

from app.main import create_app


class TestHistoryApiEndpoints(unittest.TestCase):
    """Test suite covering GET /api/v1/market-data/history/{symbol}."""

    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_get_history_default(self):
        """GET /api/v1/market-data/history/AAPL returns 200 with 30-day (1M) daily bars."""
        response = self.client.get("/api/v1/market-data/history/AAPL")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("data", payload)
        self.assertIn("meta", payload)

        data = payload["data"]
        self.assertGreater(len(data), 0)
        first_bar = data[0]
        self.assertEqual(first_bar["symbol"], "AAPL")
        self.assertIn("open", first_bar)
        self.assertIn("high", first_bar)
        self.assertIn("low", first_bar)
        self.assertIn("close", first_bar)
        self.assertIn("volume", first_bar)
        self.assertIn("timestamp", first_bar)

        meta = payload["meta"]
        self.assertEqual(meta["symbol"], "AAPL")
        self.assertEqual(meta["interval"], "1d")
        self.assertEqual(meta["range"], "1M")
        self.assertEqual(meta["count"], len(data))
        self.assertIn("source", meta)
        self.assertIn("min_price", meta)
        self.assertIn("max_price", meta)
        self.assertIn("first_close", meta)
        self.assertIn("last_close", meta)
        self.assertIn("period_change", meta)
        self.assertIn("period_change_percent", meta)

    def test_get_history_with_range_1w(self):
        """GET /api/v1/market-data/history/AAPL?range=1W returns 200 with ~7 days."""
        response = self.client.get("/api/v1/market-data/history/AAPL?range=1W")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["range"], "1W")
        self.assertLessEqual(payload["meta"]["count"], 8)

    def test_get_history_with_range_1y(self):
        """GET /api/v1/market-data/history/MSFT?range=1Y returns 200 with ~365 days."""
        response = self.client.get("/api/v1/market-data/history/MSFT?range=1Y&interval=1d")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["range"], "1Y")
        self.assertGreater(payload["meta"]["count"], 300)

    def test_get_history_with_range_5y(self):
        """GET /api/v1/market-data/history/GOOGL?range=5Y returns 200 with weekly bars."""
        response = self.client.get("/api/v1/market-data/history/GOOGL?range=5Y&interval=1wk")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["range"], "5Y")
        self.assertEqual(payload["meta"]["interval"], "1wk")
        self.assertGreater(payload["meta"]["count"], 200)

    def test_get_history_with_days(self):
        """GET /api/v1/market-data/history/AAPL?days=14 returns 200 with 14-day history."""
        response = self.client.get("/api/v1/market-data/history/AAPL?days=14")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertLessEqual(payload["meta"]["count"], 15)

    def test_get_history_with_explicit_dates(self):
        """GET /api/v1/market-data/history/AAPL?start=...&end=... returns exact date range."""
        start = "2026-01-01T00:00:00Z"
        end = "2026-01-10T00:00:00Z"
        response = self.client.get(f"/api/v1/market-data/history/AAPL?start={start}&end={end}&interval=1d")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["count"], 10)

    def test_get_history_invalid_range_raises_validation_error(self):
        """GET /api/v1/market-data/history/AAPL?range=INVALID returns 400 validation error."""
        response = self.client.get("/api/v1/market-data/history/AAPL?range=INVALID")
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertIn("error", payload)
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")

    def test_get_history_invalid_dates_order_raises_validation_error(self):
        """GET /api/v1/market-data/history/AAPL with start after end returns 400."""
        start = "2026-02-01T00:00:00Z"
        end = "2026-01-01T00:00:00Z"
        response = self.client.get(f"/api/v1/market-data/history/AAPL?start={start}&end={end}")
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertIn("error", payload)
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")

    def test_get_history_unknown_symbol_returns_404(self):
        """GET /api/v1/market-data/history/UNKNOWN_TICKER returns 404."""
        response = self.client.get("/api/v1/market-data/history/UNKNOWN_TICKER")
        self.assertEqual(response.status_code, 404)
        payload = response.json()
        self.assertIn("error", payload)
        self.assertEqual(payload["error"]["code"], "RESOURCE_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
