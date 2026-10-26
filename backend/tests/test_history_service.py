"""Unit tests covering HistoryService, timeframe resolution, interval validation, and bar integrity."""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from app.core.errors import InstrumentNotFoundError, ValidationError
from app.providers.base import ProviderBar
from app.providers.mock import MockMarketDataProvider
from app.services.history import (
    DEFAULT_INTERVAL_FOR_RANGE,
    HistoricalSeries,
    HistoryService,
    SUPPORTED_TIMEFRAME_RANGES,
    normalize_interval,
    resolve_time_window,
    sanitize_symbol,
    validate_and_sort_bars,
)


class TestHistoryServiceUnit(unittest.TestCase):
    """Test suite covering historical data service validation and helpers."""

    def test_sanitize_symbol_valid(self):
        self.assertEqual(sanitize_symbol("aapl"), "AAPL")
        self.assertEqual(sanitize_symbol("  msft  "), "MSFT")
        self.assertEqual(sanitize_symbol("BTC-USD"), "BTC-USD")
        self.assertEqual(sanitize_symbol("BRK.B"), "BRK.B")
        self.assertEqual(sanitize_symbol("ETH/USD"), "ETH/USD")
        self.assertEqual(sanitize_symbol("^GSPC"), "^GSPC")

    def test_sanitize_symbol_invalid(self):
        with self.assertRaises(ValidationError):
            sanitize_symbol("")
        with self.assertRaises(ValidationError):
            sanitize_symbol("   ")
        with self.assertRaises(ValidationError):
            sanitize_symbol("INVALID SYMBOL WITH SPACES")
        with self.assertRaises(ValidationError):
            sanitize_symbol("A" * 35)
        with self.assertRaises(ValidationError):
            sanitize_symbol("AAPL;DROP TABLE")

    def test_normalize_interval(self):
        self.assertEqual(normalize_interval("1d"), "1d")
        self.assertEqual(normalize_interval("1D"), "1d")
        self.assertEqual(normalize_interval("1w"), "1wk")
        self.assertEqual(normalize_interval("1wk"), "1wk")
        self.assertEqual(normalize_interval("1WK"), "1wk")
        self.assertEqual(normalize_interval("1m"), "1mo")
        self.assertEqual(normalize_interval("1mo"), "1mo")
        self.assertEqual(normalize_interval("1h"), "1h")
        self.assertEqual(normalize_interval("5m"), "5m")
        self.assertEqual(normalize_interval("15m"), "15m")

        # Range-based defaults
        self.assertEqual(normalize_interval(None, range_key="5Y"), "1wk")
        self.assertEqual(normalize_interval("", range_key="1M"), "1d")
        self.assertEqual(normalize_interval(None, range_key=None), "1d")

        # Unsupported interval
        with self.assertRaises(ValidationError):
            normalize_interval("2h")
        with self.assertRaises(ValidationError):
            normalize_interval("invalid_interval")

    def test_resolve_time_window_by_range(self):
        for range_code in ("1D", "1W", "1M", "3M", "6M", "1Y", "5Y", "ALL"):
            start, end, tag = resolve_time_window(range_str=range_code)
            self.assertEqual(tag, range_code)
            self.assertLess(start, end)
            expected_delta = SUPPORTED_TIMEFRAME_RANGES[range_code]
            actual_delta = end - start
            self.assertAlmostEqual(actual_delta.total_seconds(), expected_delta.total_seconds(), delta=5)

    def test_resolve_time_window_by_range_case_insensitive(self):
        start, end, tag = resolve_time_window(range_str="  1m  ")
        self.assertEqual(tag, "1M")
        self.assertLess(start, end)

    def test_resolve_time_window_by_range_unsupported(self):
        with self.assertRaises(ValidationError) as ctx:
            resolve_time_window(range_str="10Y")
        self.assertIn("Unsupported timeframe range", str(ctx.exception))

    def test_resolve_time_window_by_days(self):
        start, end, tag = resolve_time_window(days=45)
        self.assertLess(start, end)
        self.assertAlmostEqual((end - start).days, 45, delta=1)

    def test_resolve_time_window_by_days_validation(self):
        with self.assertRaises(ValidationError):
            resolve_time_window(days=0)
        with self.assertRaises(ValidationError):
            resolve_time_window(days=-10)
        with self.assertRaises(ValidationError):
            resolve_time_window(days=2500)

    def test_resolve_time_window_explicit_dates(self):
        start = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        end = datetime(2026, 2, 1, 10, 0, tzinfo=timezone.utc)
        s, e, tag = resolve_time_window(start=start, end=end)
        self.assertEqual(s, start)
        self.assertEqual(e, end)
        self.assertIsNone(tag)

    def test_resolve_time_window_explicit_dates_naive_timezone(self):
        start = datetime(2026, 1, 1)
        end = datetime(2026, 2, 1)
        s, e, _ = resolve_time_window(start=start, end=end)
        self.assertEqual(s.tzinfo, timezone.utc)
        self.assertEqual(e.tzinfo, timezone.utc)

    def test_resolve_time_window_explicit_dates_invalid_order(self):
        start = datetime(2026, 2, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with self.assertRaises(ValidationError) as ctx:
            resolve_time_window(start=start, end=end)
        self.assertIn("must be strictly before", str(ctx.exception))

    def test_resolve_time_window_explicit_dates_future_start(self):
        start = datetime.now(timezone.utc) + timedelta(days=10)
        end = start + timedelta(days=5)
        with self.assertRaises(ValidationError) as ctx:
            resolve_time_window(start=start, end=end)
        self.assertIn("cannot be in the future", str(ctx.exception))

    def test_resolve_time_window_default(self):
        start, end, tag = resolve_time_window()
        self.assertEqual(tag, "1M")
        self.assertAlmostEqual((end - start).days, 30, delta=1)

    def test_validate_and_sort_bars_integrity(self):
        t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 2, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 3, tzinfo=timezone.utc)

        raw_bars = [
            ProviderBar("AAPL", t1, Decimal("100"), Decimal("105"), Decimal("99"), Decimal("104"), Decimal("1000")),
            ProviderBar("AAPL", t0, Decimal("98"), Decimal("102"), Decimal("97"), Decimal("100"), Decimal("1200")),
            ProviderBar("AAPL", t2, Decimal("104"), Decimal("108"), Decimal("103"), Decimal("107"), Decimal("1500")),
        ]

        sorted_bars = validate_and_sort_bars(raw_bars, "AAPL")
        self.assertEqual(len(sorted_bars), 3)
        self.assertEqual(sorted_bars[0].timestamp, t0)
        self.assertEqual(sorted_bars[1].timestamp, t1)
        self.assertEqual(sorted_bars[2].timestamp, t2)

    def test_validate_and_sort_bars_corrupt_high_low(self):
        t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        corrupt = [
            ProviderBar("AAPL", t0, Decimal("100"), Decimal("90"), Decimal("105"), Decimal("95"), Decimal("1000"))
        ]
        with self.assertRaises(ValidationError) as ctx:
            validate_and_sort_bars(corrupt, "AAPL")
        self.assertIn("High (90) is lower than Low (105)", str(ctx.exception))

    def test_validate_and_sort_bars_deduplicate(self):
        t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        bars = [
            ProviderBar("AAPL", t0, Decimal("100"), Decimal("105"), Decimal("99"), Decimal("104"), Decimal("1000")),
            ProviderBar("AAPL", t0, Decimal("100"), Decimal("105"), Decimal("99"), Decimal("104"), Decimal("1000")),
        ]
        res = validate_and_sort_bars(bars, "AAPL")
        self.assertEqual(len(res), 1)

    def test_validate_and_sort_bars_zero_fabrication(self):
        # Authentically skip weekends (Jan 2, Jan 5 -> skipping Jan 3, Jan 4)
        t_friday = datetime(2026, 1, 2, tzinfo=timezone.utc)
        t_monday = datetime(2026, 1, 5, tzinfo=timezone.utc)
        bars = [
            ProviderBar("AAPL", t_friday, Decimal("100"), Decimal("105"), Decimal("99"), Decimal("104"), Decimal("1000")),
            ProviderBar("AAPL", t_monday, Decimal("105"), Decimal("109"), Decimal("104"), Decimal("108"), Decimal("1200")),
        ]
        res = validate_and_sort_bars(bars, "AAPL")
        self.assertEqual(len(res), 2)
        # Ensure no fabricated weekend points were artificially inserted
        self.assertEqual(res[0].timestamp, t_friday)
        self.assertEqual(res[1].timestamp, t_monday)


class TestHistoryServiceIntegration(unittest.TestCase):
    """Test suite covering HistoryService with MockMarketDataProvider."""

    def setUp(self):
        self.provider = MockMarketDataProvider()
        self.service = HistoryService(provider=self.provider)

    def test_get_historical_series_default_range(self):
        series = asyncio.run(self.service.get_historical_series("AAPL"))
        self.assertIsInstance(series, HistoricalSeries)
        self.assertEqual(series.symbol, "AAPL")
        self.assertEqual(series.range, "1M")
        self.assertEqual(series.interval, "1d")
        self.assertGreater(series.count, 0)
        self.assertEqual(len(series.bars), series.count)
        self.assertIsNotNone(series.min_price)
        self.assertIsNotNone(series.max_price)
        self.assertGreaterEqual(series.max_price, series.min_price)
        self.assertIsNotNone(series.period_change)
        self.assertIsNotNone(series.period_change_percent)

    def test_get_historical_series_range_1y(self):
        series = asyncio.run(self.service.get_historical_series("MSFT", range_str="1Y", interval="1d"))
        self.assertEqual(series.symbol, "MSFT")
        self.assertEqual(series.range, "1Y")
        self.assertEqual(series.interval, "1d")
        self.assertGreater(series.count, 300)

    def test_get_historical_series_range_5y_weekly(self):
        series = asyncio.run(self.service.get_historical_series("GOOGL", range_str="5Y", interval="1wk"))
        self.assertEqual(series.symbol, "GOOGL")
        self.assertEqual(series.range, "5Y")
        self.assertEqual(series.interval, "1wk")
        self.assertGreater(series.count, 200)

    def test_get_historical_series_days_parameter(self):
        series = asyncio.run(self.service.get_historical_series("AAPL", days=10))
        self.assertEqual(series.symbol, "AAPL")
        self.assertLessEqual(series.count, 11)

    def test_get_historical_series_unknown_symbol_raises(self):
        with self.assertRaises(InstrumentNotFoundError):
            asyncio.run(self.service.get_historical_series("NONEXISTENT_XYZ"))

    def test_get_historical_series_invalid_symbol_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            asyncio.run(self.service.get_historical_series("$$$"))

    def test_get_historical_series_provider_error_propagation(self):
        self.provider.simulate_error(RuntimeError("Simulated upstream provider outage"))
        with self.assertRaises(RuntimeError):
            asyncio.run(self.service.get_historical_series("AAPL"))
        self.provider.clear_simulated_error()


if __name__ == "__main__":
    unittest.main()
