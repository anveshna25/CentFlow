import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from app.core.errors import (
    InstrumentNotFoundError,
    ProviderResponseError,
    ProviderTimeoutError,
    StaleDataError,
    ValidationError,
)
from app.providers.base import BaseMarketDataProvider, ProviderCapabilities, ProviderQuote, ProviderStatus
from app.providers.mock import MockMarketDataProvider
from app.services.quote import (
    MarketQuote,
    QuoteService,
    calculate_staleness,
    determine_market_status,
    get_us_eastern_time,
    sanitize_symbol,
    validate_and_normalize_quote,
)


class DummyCustomProvider(BaseMarketDataProvider):
    """Custom provider to inject anomalous quotes for testing edge-case validation."""

    def __init__(self, quote_to_return: ProviderQuote) -> None:
        self._quote = quote_to_return

    @property
    def name(self) -> str:
        return "dummy_test"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(is_delayed=True, delay_minutes=15)

    async def get_quote(self, symbol: str) -> ProviderQuote:
        return self._quote

    async def get_historical_bars(self, *args, **kwargs):
        return []

    async def search_instruments(self, query: str):
        return []

    async def get_status(self) -> ProviderStatus:
        return ProviderStatus(name="dummy_test", is_active=True)


class TestQuoteValidationAndSanitization(unittest.TestCase):
    """Unit tests for symbol sanitization and quote numeric validations."""

    def test_sanitize_symbol_valid(self):
        self.assertEqual(sanitize_symbol("aapl"), "AAPL")
        self.assertEqual(sanitize_symbol("  msft  "), "MSFT")
        self.assertEqual(sanitize_symbol("btc-usd"), "BTC-USD")
        self.assertEqual(sanitize_symbol("BRK.B"), "BRK.B")

    def test_sanitize_symbol_invalid(self):
        with self.assertRaises(ValidationError):
            sanitize_symbol("")
        with self.assertRaises(ValidationError):
            sanitize_symbol("   ")
        with self.assertRaises(ValidationError):
            sanitize_symbol(None)  # type: ignore
        with self.assertRaises(ValidationError):
            sanitize_symbol("AAPL MSFT")  # internal whitespace

    def test_price_validation_negative_raises_error(self):
        provider = MockMarketDataProvider()
        invalid_quote = ProviderQuote(
            symbol="TEST",
            price=Decimal("-10.50"),
            currency="USD",
            timestamp=datetime.now(timezone.utc),
        )
        with self.assertRaises(ProviderResponseError) as ctx:
            validate_and_normalize_quote(invalid_quote, provider, staleness_threshold=900)
        self.assertIn("Invalid non-positive quote price", str(ctx.exception))

    def test_price_validation_zero_raises_error(self):
        provider = MockMarketDataProvider()
        invalid_quote = ProviderQuote(
            symbol="TEST",
            price=Decimal("0.00"),
            currency="USD",
            timestamp=datetime.now(timezone.utc),
        )
        with self.assertRaises(ProviderResponseError):
            validate_and_normalize_quote(invalid_quote, provider, staleness_threshold=900)

    def test_high_low_swap_if_inverted(self):
        provider = MockMarketDataProvider()
        inverted_quote = ProviderQuote(
            symbol="TEST",
            price=Decimal("100.00"),
            currency="USD",
            timestamp=datetime.now(timezone.utc),
            high=Decimal("95.00"),
            low=Decimal("105.00"),  # high < low
        )
        normalized = validate_and_normalize_quote(inverted_quote, provider, staleness_threshold=900)
        self.assertEqual(normalized.high, Decimal("105.00"))
        self.assertEqual(normalized.low, Decimal("95.00"))

    def test_negative_volume_clamped_to_zero(self):
        provider = MockMarketDataProvider()
        quote = ProviderQuote(
            symbol="TEST",
            price=Decimal("100.00"),
            currency="USD",
            timestamp=datetime.now(timezone.utc),
            volume=Decimal("-500"),
        )
        normalized = validate_and_normalize_quote(quote, provider, staleness_threshold=900)
        self.assertEqual(normalized.volume, Decimal("0"))

    def test_derived_change_and_percent(self):
        provider = MockMarketDataProvider()
        # Only price and previous_close provided
        quote = ProviderQuote(
            symbol="TEST",
            price=Decimal("110.00"),
            currency="USD",
            timestamp=datetime.now(timezone.utc),
            previous_close=Decimal("100.00"),
            change=None,
            change_percent=None,
        )
        normalized = validate_and_normalize_quote(quote, provider, staleness_threshold=900)
        self.assertEqual(normalized.change, Decimal("10.00"))
        self.assertEqual(normalized.change_percent, Decimal("10.00"))

    def test_derived_previous_close_from_change(self):
        provider = MockMarketDataProvider()
        quote = ProviderQuote(
            symbol="TEST",
            price=Decimal("150.00"),
            currency="USD",
            timestamp=datetime.now(timezone.utc),
            previous_close=None,
            change=Decimal("15.00"),
        )
        normalized = validate_and_normalize_quote(quote, provider, staleness_threshold=900)
        self.assertEqual(normalized.previous_close, Decimal("135.00"))


class TestMarketStatusAndFreshness(unittest.TestCase):
    """Unit tests for market session status and freshness/staleness calculation."""

    def test_crypto_market_is_always_open(self):
        self.assertEqual(determine_market_status("BTC-USD"), "OPEN")
        self.assertEqual(determine_market_status("ETH-USD"), "OPEN")
        self.assertEqual(determine_market_status("BTC"), "OPEN")

    def test_us_eastern_conversion(self):
        # Summer date (EDT = UTC-4): July 15, 2026, 14:00 UTC -> 10:00 EDT
        utc_summer = datetime(2026, 7, 15, 14, 0, tzinfo=timezone.utc)
        et_summer = get_us_eastern_time(utc_summer)
        self.assertEqual(et_summer.hour, 10)
        self.assertEqual(et_summer.utcoffset(), timedelta(hours=-4))

        # Winter date (EST = UTC-5): December 15, 2026, 15:00 UTC -> 10:00 EST
        utc_winter = datetime(2026, 12, 15, 15, 0, tzinfo=timezone.utc)
        et_winter = get_us_eastern_time(utc_winter)
        self.assertEqual(et_winter.hour, 10)
        self.assertEqual(et_winter.utcoffset(), timedelta(hours=-5))

    def test_equity_market_status_regular_hours(self):
        # Wednesday July 15, 2026 at 15:00 UTC is 11:00 AM EDT -> Regular hours (OPEN)
        wednesday_midday = datetime(2026, 7, 15, 15, 0, tzinfo=timezone.utc)
        self.assertEqual(determine_market_status("AAPL", reference_time=wednesday_midday), "OPEN")

    def test_equity_market_status_premarket(self):
        # Wednesday July 15, 2026 at 11:00 UTC is 07:00 AM EDT -> Pre-market (EXTENDED)
        wednesday_pre = datetime(2026, 7, 15, 11, 0, tzinfo=timezone.utc)
        self.assertEqual(determine_market_status("AAPL", reference_time=wednesday_pre), "EXTENDED")

    def test_equity_market_status_afterhours(self):
        # Wednesday July 15, 2026 at 21:00 UTC is 17:00 (5:00 PM) EDT -> After-hours (EXTENDED)
        wednesday_post = datetime(2026, 7, 15, 21, 0, tzinfo=timezone.utc)
        self.assertEqual(determine_market_status("AAPL", reference_time=wednesday_post), "EXTENDED")

    def test_equity_market_status_weekend_closed(self):
        # Sunday July 19, 2026 at 18:00 UTC -> Weekend (CLOSED)
        sunday = datetime(2026, 7, 19, 18, 0, tzinfo=timezone.utc)
        self.assertEqual(determine_market_status("AAPL", reference_time=sunday), "CLOSED")

    def test_staleness_fresh_quote(self):
        now = datetime.now(timezone.utc)
        quote_time = now - timedelta(seconds=60)
        staleness_seconds, is_stale = calculate_staleness(quote_time, now, threshold_seconds=900, market_status="OPEN")
        self.assertEqual(staleness_seconds, 60)
        self.assertFalse(is_stale)

    def test_staleness_stale_open_market(self):
        now = datetime.now(timezone.utc)
        quote_time = now - timedelta(seconds=1200)  # 20 minutes old
        staleness_seconds, is_stale = calculate_staleness(quote_time, now, threshold_seconds=900, market_status="OPEN")
        self.assertEqual(staleness_seconds, 1200)
        self.assertTrue(is_stale)


class TestQuoteServiceAsync(unittest.IsolatedAsyncioTestCase):
    """End-to-end service testing for QuoteService operations."""

    async def asyncSetUp(self):
        self.mock_provider = MockMarketDataProvider()
        self.service = QuoteService(provider=self.mock_provider, enable_cache=False)

    async def test_get_quote_success(self):
        quote = await self.service.get_quote("AAPL")
        self.assertIsInstance(quote, MarketQuote)
        self.assertEqual(quote.symbol, "AAPL")
        self.assertEqual(quote.price, Decimal("185.50"))
        self.assertEqual(quote.currency, "USD")
        self.assertEqual(quote.data_source, "mock")
        self.assertEqual(quote.delay_minutes, 0)
        self.assertIsNotNone(quote.timestamp)
        self.assertIn(quote.market_status, ["OPEN", "CLOSED", "EXTENDED"])

    async def test_get_quote_case_and_whitespace_insensitivity(self):
        quote = await self.service.get_quote("   msft   ")
        self.assertEqual(quote.symbol, "MSFT")
        self.assertEqual(quote.price, Decimal("420.25"))

    async def test_get_quote_unknown_symbol_raises_not_found(self):
        with self.assertRaises(InstrumentNotFoundError):
            await self.service.get_quote("NONEXISTENT_XYZ")

    async def test_get_quote_blank_symbol_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            await self.service.get_quote("   ")

    async def test_get_quote_provider_error_propagates(self):
        self.mock_provider.simulate_error(ProviderTimeoutError("mock", "Simulated timeout"))
        with self.assertRaises(ProviderTimeoutError):
            await self.service.get_quote("AAPL")

    async def test_get_quote_strict_staleness_check_raises(self):
        # Create quote with timestamp 1 hour ago
        old_time = datetime.now(timezone.utc) - timedelta(hours=1)
        stale_raw_quote = ProviderQuote(
            symbol="OLD",
            price=Decimal("50.00"),
            currency="USD",
            timestamp=old_time,
        )
        dummy_provider = DummyCustomProvider(stale_raw_quote)
        service = QuoteService(provider=dummy_provider, enable_cache=False)

        # Asking for max_staleness_seconds=60 should raise StaleDataError
        with self.assertRaises(StaleDataError) as ctx:
            await service.get_quote("OLD", max_staleness_seconds=60)
        self.assertEqual(ctx.exception.code, "STALE_MARKET_DATA")

    async def test_get_quotes_batch_success(self):
        quotes = await self.service.get_quotes(["AAPL", "MSFT", "BTC-USD"])
        self.assertEqual(len(quotes), 3)
        symbols = [q.symbol for q in quotes]
        self.assertEqual(symbols, ["AAPL", "MSFT", "BTC-USD"])

    async def test_get_quotes_batch_deduplication(self):
        quotes = await self.service.get_quotes(["AAPL", "aapl", " AAPL "])
        self.assertEqual(len(quotes), 1)
        self.assertEqual(quotes[0].symbol, "AAPL")

    async def test_get_quotes_batch_partial_success(self):
        # One valid, one invalid
        quotes = await self.service.get_quotes(["AAPL", "NONEXISTENT_XYZ"], allow_partial=True)
        self.assertEqual(len(quotes), 1)
        self.assertEqual(quotes[0].symbol, "AAPL")

    async def test_get_quotes_batch_partial_false_raises(self):
        with self.assertRaises(InstrumentNotFoundError):
            await self.service.get_quotes(["AAPL", "NONEXISTENT_XYZ"], allow_partial=False)

    async def test_get_quotes_empty_input(self):
        quotes = await self.service.get_quotes([])
        self.assertEqual(quotes, [])


if __name__ == "__main__":
    unittest.main()
