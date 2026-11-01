from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, CircuitState
from app.core.errors import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    sanitize_provider_error,
)
from app.main import create_app
from app.providers.base import BaseMarketDataProvider, ProviderCapabilities, ProviderQuote, ProviderStatus
from app.providers.cache import CachedMarketDataProvider
from app.providers.mock import MockMarketDataProvider
from app.services.market_data import MarketDataService
from app.services.quote import format_freshness_label


class BrokenProvider(BaseMarketDataProvider):
    """Mock provider designed to simulate outages, rate limits, or timeouts."""

    def __init__(self, name: str = "broken_feed") -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities()

    async def get_quote(self, symbol: str) -> ProviderQuote:
        raise TimeoutError("Connection to feed timed out after 5000ms")

    async def get_historical_bars(self, *args, **kwargs):
        raise ConnectionRefusedError("Feed server refused connection")

    async def search_instruments(self, query: str = "", asset_type=None):
        raise RuntimeError("Internal upstream server error 500")

    async def get_status(self) -> ProviderStatus:
        return ProviderStatus(name=self._name, is_active=False, message="Simulated feed outage")


class TestProviderErrorSanitization(unittest.TestCase):
    """Test suite verifying error masking and safe exception categorization."""

    def test_sanitize_timeout_error(self):
        err = sanitize_provider_error(TimeoutError("request timed out"), "yahoo")
        self.assertIsInstance(err, ProviderTimeoutError)
        self.assertEqual(err.code, "PROVIDER_TIMEOUT")
        self.assertIn("timed out", err.message)
        self.assertNotIn("Traceback", err.message)

    def test_sanitize_rate_limit_error(self):
        err = sanitize_provider_error(Exception("HTTP 429 Too Many Requests"), "polygon")
        self.assertIsInstance(err, ProviderRateLimitError)
        self.assertEqual(err.code, "PROVIDER_RATE_LIMIT")
        self.assertEqual(err.status_code, 429)

    def test_sanitize_auth_error(self):
        err = sanitize_provider_error(Exception("Invalid API key 401 Unauthorized"), "fmp")
        self.assertIsInstance(err, ProviderAuthenticationError)
        self.assertEqual(err.code, "PROVIDER_AUTHENTICATION_ERROR")

    def test_sanitize_malformed_response_error(self):
        err = sanitize_provider_error(KeyError("quoteResponse"), "yahoo")
        self.assertIsInstance(err, ProviderResponseError)
        self.assertEqual(err.code, "PROVIDER_RESPONSE_ERROR")

    def test_sanitize_unreachable_network_error(self):
        err = sanitize_provider_error(ConnectionRefusedError("Connection refused by peer"), "feed")
        self.assertIsInstance(err, ProviderUnavailableError)
        self.assertEqual(err.code, "PROVIDER_UNAVAILABLE")

    def test_sanitize_generic_error_prevents_leaks(self):
        err = sanitize_provider_error(
            RuntimeError("Sensitive token xyz123 at https://api.secret.internal/v1"),
            "secret_feed",
        )
        self.assertIsInstance(err, ProviderError)
        self.assertEqual(err.code, "PROVIDER_ERROR")
        self.assertNotIn("xyz123", err.message)
        self.assertNotIn("secret.internal", err.message)


class TestFreshnessIndicatorFormatting(unittest.TestCase):
    """Test suite verifying human-readable data freshness calculations."""

    def test_real_time_freshness(self):
        now = datetime.now(timezone.utc)
        self.assertEqual(format_freshness_label(now, now), "Real-time")
        self.assertEqual(format_freshness_label(now - timedelta(seconds=5), now), "Real-time")

    def test_seconds_ago_freshness(self):
        now = datetime.now(timezone.utc)
        label = format_freshness_label(now - timedelta(seconds=25), now)
        self.assertEqual(label, "Updated 25s ago")

    def test_minutes_ago_freshness(self):
        now = datetime.now(timezone.utc)
        label = format_freshness_label(now - timedelta(minutes=4), now)
        self.assertEqual(label, "Updated 4m ago")

    def test_hours_ago_freshness(self):
        now = datetime.now(timezone.utc)
        label = format_freshness_label(now - timedelta(hours=3), now)
        self.assertEqual(label, "Updated 3h ago")

    def test_delayed_freshness(self):
        now = datetime.now(timezone.utc)
        label = format_freshness_label(now, now, delay_minutes=15)
        self.assertEqual(label, "Delayed 15m")

    def test_stale_cached_freshness(self):
        now = datetime.now(timezone.utc)
        label = format_freshness_label(now - timedelta(minutes=12), now, is_stale=True)
        self.assertEqual(label, "Stale (cached 12m ago)")


class TestCachedProviderCircuitBreakerAndFailover(unittest.IsolatedAsyncioTestCase):
    """Test suite verifying circuit breaker failover and graceful caching degradation."""

    async def test_failover_to_fallback_provider_when_primary_breaks(self):
        broken = BrokenProvider("primary_feed")
        fallback = MockMarketDataProvider()
        cb = CircuitBreaker("primary_feed", failure_threshold=2, recovery_timeout=0.5)

        cached_provider = CachedMarketDataProvider(
            provider=broken,
            circuit_breaker=cb,
            fallback_provider=fallback,
            quote_ttl=10.0,
        )

        # Primary fails -> failover to fallback provider
        quote = await cached_provider.get_quote("AAPL")
        self.assertIsNotNone(quote)
        self.assertEqual(quote.symbol, "AAPL")
        self.assertTrue(quote.is_stale)
        self.assertEqual(cb.consecutive_failures, 1)

        # Second failure trips breaker to OPEN and continues using fallback
        quote2 = await cached_provider.get_quote("AAPL")
        self.assertIsNotNone(quote2)
        self.assertEqual(cb.state, CircuitState.OPEN)

    async def test_failover_to_stale_in_memory_cache_during_circuit_open(self):
        mock_primary = MockMarketDataProvider()
        cb = CircuitBreaker("test_cb", failure_threshold=2, recovery_timeout=1.0)
        cached_provider = CachedMarketDataProvider(
            provider=mock_primary,
            circuit_breaker=cb,
            quote_ttl=0.01,
            stale_grace_ttl=60.0,
        )

        # Initial populate
        q1 = await cached_provider.get_quote("AAPL")
        self.assertFalse(q1.is_stale)

        # Trip breaker
        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)

        # Serves from stale cache without hitting provider
        q2 = await cached_provider.get_quote("AAPL")
        self.assertEqual(q2.symbol, "AAPL")
        self.assertTrue(q2.is_stale)


class TestProviderResilienceHttpEndpoints(unittest.TestCase):
    """HTTP integration tests verifying diagnostics and freshness in API responses."""

    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_provider_status_endpoint_includes_circuit_breaker(self):
        response = self.client.get("/api/v1/market-data/status")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("data", payload)
        data = payload["data"]
        self.assertIn("name", data)
        self.assertIn("is_active", data)
        # Verify circuit breaker diagnostics are present in status
        self.assertIn("circuit_breaker", data)
        if data["circuit_breaker"]:
            self.assertIn("state", data["circuit_breaker"])
            self.assertEqual(data["circuit_breaker"]["state"], "CLOSED")

    def test_quote_endpoint_includes_freshness_label(self):
        response = self.client.get("/api/v1/market-data/quotes/AAPL")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("data", payload)
        data = payload["data"]
        self.assertIn("freshness_label", data)
        self.assertIsNotNone(data["freshness_label"])
        self.assertIn("freshness_label", payload.get("meta", {}))


if __name__ == "__main__":
    unittest.main()
