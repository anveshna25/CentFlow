import json
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import httpx

from app.core.config import Settings
from app.core.errors import InstrumentNotFoundError, ProviderUnavailableError
from app.providers.base import ProviderBar, ProviderInstrument, ProviderQuote, ProviderStatus
from app.providers.registry import ProviderRegistry
from app.providers.yahoo import YahooMarketDataProvider


class TestYahooMarketDataProvider(unittest.IsolatedAsyncioTestCase):
    """Test suite for YahooMarketDataProvider with deterministic mock HTTP transport."""

    def setUp(self) -> None:
        self.sample_quote_response = {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "currency": "USD",
                            "symbol": "AAPL",
                            "exchangeName": "NMS",
                            "instrumentType": "EQUITY",
                            "regularMarketPrice": 185.50,
                            "chartPreviousClose": 183.90,
                            "previousClose": 183.90,
                            "regularMarketOpen": 184.20,
                            "regularMarketDayHigh": 186.10,
                            "regularMarketDayLow": 183.80,
                            "regularMarketVolume": 52400000,
                            "regularMarketTime": 1713900000,
                        },
                        "timestamp": [1713900000],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [184.20],
                                    "high": [186.10],
                                    "low": [183.80],
                                    "close": [185.50],
                                    "volume": [52400000],
                                }
                            ]
                        },
                    }
                ],
                "error": None,
            }
        }

        self.sample_history_response = {
            "chart": {
                "result": [
                    {
                        "meta": {"symbol": "AAPL", "currency": "USD"},
                        "timestamp": [1713700000, 1713800000, 1713900000],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [182.00, None, 184.20],
                                    "high": [183.50, None, 186.10],
                                    "low": [181.50, None, 183.80],
                                    "close": [183.00, None, 185.50],
                                    "volume": [48000000, None, 52400000],
                                }
                            ]
                        },
                    }
                ],
                "error": None,
            }
        }

        self.sample_search_response = {
            "quotes": [
                {
                    "symbol": "AAPL",
                    "shortname": "Apple Inc.",
                    "quoteType": "EQUITY",
                    "exchange": "NMS",
                    "dispExchange": "NASDAQ",
                },
                {
                    "symbol": "BTC-USD",
                    "shortname": "Bitcoin USD",
                    "quoteType": "CRYPTOCURRENCY",
                    "exchange": "CCC",
                    "dispExchange": "Coinbase",
                },
            ]
        }

    async def test_provider_name_and_status(self) -> None:
        """Provider name should be 'yahoo' and status report active."""
        provider = YahooMarketDataProvider()
        self.assertEqual(provider.name, "yahoo")

        status = await provider.get_status()
        self.assertIsInstance(status, ProviderStatus)
        self.assertEqual(status.name, "yahoo")
        self.assertTrue(status.is_active)
        await provider.close()

    async def test_get_quote_success(self) -> None:
        """Normalized quote should be correctly parsed from Yahoo Finance chart payload."""
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertIn("/v8/finance/chart/AAPL", str(request.url))
            return httpx.Response(200, json=self.sample_quote_response)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            provider = YahooMarketDataProvider(client=client)
            quote = await provider.get_quote("AAPL")

            self.assertIsInstance(quote, ProviderQuote)
            self.assertEqual(quote.symbol, "AAPL")
            self.assertEqual(quote.price, Decimal("185.50"))
            self.assertEqual(quote.currency, "USD")
            self.assertEqual(quote.open, Decimal("184.20"))
            self.assertEqual(quote.high, Decimal("186.10"))
            self.assertEqual(quote.low, Decimal("183.80"))
            self.assertEqual(quote.previous_close, Decimal("183.90"))
            self.assertEqual(quote.volume, Decimal("52400000"))
            self.assertEqual(quote.change, Decimal("1.60"))
            self.assertEqual(quote.change_percent, Decimal("0.87"))

    async def test_get_quote_not_found_on_404(self) -> None:
        """InstrumentNotFoundError should be raised when Yahoo returns 404."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"chart": {"error": {"code": "Not Found"}}})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            provider = YahooMarketDataProvider(client=client)
            with self.assertRaises(InstrumentNotFoundError) as ctx:
                await provider.get_quote("UNKNOWN")
            self.assertIn("UNKNOWN", str(ctx.exception))

    async def test_get_quote_error_in_payload(self) -> None:
        """InstrumentNotFoundError should be raised when chart payload contains error."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"chart": {"result": None, "error": {"description": "Symbol not found"}}})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            provider = YahooMarketDataProvider(client=client)
            with self.assertRaises(InstrumentNotFoundError):
                await provider.get_quote("INVALID")

    async def test_get_quote_http_500_raises_provider_unavailable(self) -> None:
        """ProviderUnavailableError should be raised when upstream service returns 500."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error")

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            provider = YahooMarketDataProvider(client=client)
            with self.assertRaises(ProviderUnavailableError):
                await provider.get_quote("AAPL")

    async def test_get_quote_network_error(self) -> None:
        """ProviderUnavailableError should be raised on connection error."""
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("Connection timed out", request=request)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            provider = YahooMarketDataProvider(client=client)
            with self.assertRaises(ProviderUnavailableError):
                await provider.get_quote("AAPL")

    async def test_get_historical_bars_success(self) -> None:
        """Historical bars should be parsed into ProviderBar instances, skipping nulls."""
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertIn("period1=", str(request.url))
            self.assertIn("period2=", str(request.url))
            return httpx.Response(200, json=self.sample_history_response)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            provider = YahooMarketDataProvider(client=client)
            start = datetime(2026, 4, 20, tzinfo=timezone.utc)
            end = datetime(2026, 4, 24, tzinfo=timezone.utc)
            bars = await provider.get_historical_bars("AAPL", start=start, end=end, interval="1d")

            # 3 timestamps in mock, but middle one has None values -> 2 bars expected
            self.assertEqual(len(bars), 2)
            self.assertIsInstance(bars[0], ProviderBar)
            self.assertEqual(bars[0].symbol, "AAPL")
            self.assertEqual(bars[0].open, Decimal("182.00"))
            self.assertEqual(bars[0].close, Decimal("183.00"))
            self.assertEqual(bars[1].open, Decimal("184.20"))
            self.assertEqual(bars[1].close, Decimal("185.50"))

    async def test_get_historical_bars_not_found(self) -> None:
        """InstrumentNotFoundError should be raised if history returns 404."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, text="Not Found")

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            provider = YahooMarketDataProvider(client=client)
            start = datetime(2026, 1, 1, tzinfo=timezone.utc)
            end = datetime(2026, 1, 10, tzinfo=timezone.utc)
            with self.assertRaises(InstrumentNotFoundError):
                await provider.get_historical_bars("UNKNOWN", start=start, end=end)

    async def test_search_instruments_success(self) -> None:
        """Search instruments should query Yahoo search and normalize asset types."""
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertIn("q=Apple", str(request.url))
            return httpx.Response(200, json=self.sample_search_response)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            provider = YahooMarketDataProvider(client=client)
            results = await provider.search_instruments("Apple")

            self.assertEqual(len(results), 2)
            self.assertIsInstance(results[0], ProviderInstrument)
            self.assertEqual(results[0].symbol, "AAPL")
            self.assertEqual(results[0].name, "Apple Inc.")
            self.assertEqual(results[0].asset_type, "equity")
            self.assertEqual(results[0].exchange, "NMS")

            self.assertEqual(results[1].symbol, "BTC-USD")
            self.assertEqual(results[1].asset_type, "crypto")

    async def test_search_instruments_empty_query(self) -> None:
        """Search with empty string should return empty sequence without network request."""
        provider = YahooMarketDataProvider()
        results = await provider.search_instruments("   ")
        self.assertEqual(results, [])
        await provider.close()

    def test_provider_registered_in_registry(self) -> None:
        """YahooMarketDataProvider should be registered in ProviderRegistry under 'yahoo'."""
        ProviderRegistry.clear()
        provider = ProviderRegistry.get("yahoo")
        self.assertIsInstance(provider, YahooMarketDataProvider)
        self.assertEqual(provider.name, "yahoo")
        ProviderRegistry.clear()

    def test_settings_resolves_yahoo_provider(self) -> None:
        """ProviderRegistry should respect Settings.market_data_provider = 'yahoo'."""
        ProviderRegistry.clear()
        mock_settings = Settings(
            app_name="CentFlow",
            app_env="test",
            app_host="127.0.0.1",
            app_port=8000,
            database_url="sqlite:///:memory:",
            market_data_provider="yahoo",
        )
        with patch("app.providers.registry.get_settings", return_value=mock_settings):
            provider = ProviderRegistry.get()
            self.assertIsInstance(provider, YahooMarketDataProvider)
            self.assertEqual(provider.name, "yahoo")
        ProviderRegistry.clear()
