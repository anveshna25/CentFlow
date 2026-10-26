"""Integration test suite executing HTTP requests against FastAPI cache management endpoints."""

import unittest
from fastapi.testclient import TestClient

from app.main import create_app


class TestCacheApiEndpoints(unittest.TestCase):
    """Test suite covering market data cache telemetry and invalidation endpoints."""

    def setUp(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_get_cache_stats(self) -> None:
        """GET /api/v1/market-data/cache/stats returns 200 with complete telemetry schema."""
        response = self.client.get("/api/v1/market-data/cache/stats")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("data", payload)

        data = payload["data"]
        self.assertIn("enabled", data)
        self.assertIn("size", data)
        self.assertIn("max_capacity", data)
        self.assertIn("eviction_policy", data)
        self.assertIn("hits", data)
        self.assertIn("misses", data)
        self.assertIn("stale_hits", data)
        self.assertIn("evictions", data)
        self.assertIn("coalesced", data)
        self.assertIn("hit_ratio", data)
        self.assertIn("ttl_config", data)

        if data["ttl_config"] is not None:
            ttl = data["ttl_config"]
            self.assertIn("quote_ttl", ttl)
            self.assertIn("history_ttl", ttl)
            self.assertIn("search_ttl", ttl)
            self.assertIn("asset_ttl", ttl)
            self.assertIn("stale_grace_ttl", ttl)

    def test_cache_telemetry_progression(self) -> None:
        """Cache hit ratio and counters increment accurately on successive requests."""
        # 1. Clear cache to start fresh
        clear_res = self.client.post("/api/v1/market-data/cache/clear")
        self.assertEqual(clear_res.status_code, 200)

        # 2. First quote request -> Miss
        res1 = self.client.get("/api/v1/market-data/quotes/AAPL")
        self.assertEqual(res1.status_code, 200)

        stats1 = self.client.get("/api/v1/market-data/cache/stats").json()["data"]
        self.assertGreaterEqual(stats1["misses"], 1)

        # 3. Second quote request for same symbol -> Hit
        res2 = self.client.get("/api/v1/market-data/quotes/AAPL")
        self.assertEqual(res2.status_code, 200)

        stats2 = self.client.get("/api/v1/market-data/cache/stats").json()["data"]
        self.assertGreaterEqual(stats2["hits"], 1)
        self.assertGreater(stats2["hit_ratio"], 0.0)

    def test_clear_cache_all(self) -> None:
        """POST /api/v1/market-data/cache/clear removes all cached items."""
        # Prime cache with quote
        self.client.get("/api/v1/market-data/quotes/MSFT")

        response = self.client.post("/api/v1/market-data/cache/clear")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertTrue(payload["data"]["cleared"])
        self.assertIsNone(payload["data"]["prefix"])
        self.assertGreaterEqual(payload["data"]["entries_removed"], 1)

        # Cache size is now 0
        stats = self.client.get("/api/v1/market-data/cache/stats").json()["data"]
        self.assertEqual(stats["size"], 0)

    def test_clear_cache_with_prefix(self) -> None:
        """POST /api/v1/market-data/cache/clear?prefix=quote: only purges quote entries."""
        # Prime quote and search cache
        self.client.get("/api/v1/market-data/quotes/NVDA")
        self.client.get("/api/v1/market-data/instruments?q=nvidia")

        # Invalidate only quote: prefix
        response = self.client.post("/api/v1/market-data/cache/clear?prefix=quote:")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertTrue(payload["data"]["cleared"])
        self.assertEqual(payload["data"]["prefix"], "quote:")
        self.assertGreaterEqual(payload["data"]["entries_removed"], 1)

    def test_purge_expired_cache(self) -> None:
        """POST /api/v1/market-data/cache/purge executes successfully."""
        response = self.client.post("/api/v1/market-data/cache/purge")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("purged_count", payload["data"])
        self.assertGreaterEqual(payload["data"]["purged_count"], 0)
