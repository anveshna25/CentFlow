from datetime import datetime, timezone
from decimal import Decimal
import unittest

from app.analytics import (
    calculate_drawdowns,
    calculate_log_returns,
    calculate_period_return,
    calculate_price_change,
    calculate_price_summary,
    calculate_returns,
    calculate_rolling_volatility,
    to_decimal,
)


class TestAnalyticsCalculations(unittest.TestCase):
    """Test suite covering core quantitative calculations and statistical summaries."""

    def test_to_decimal_conversion(self):
        self.assertEqual(to_decimal(10), Decimal("10"))
        self.assertEqual(to_decimal(10.5), Decimal("10.5"))
        self.assertEqual(to_decimal("150.25"), Decimal("150.25"))
        self.assertEqual(to_decimal(Decimal("42")), Decimal("42"))

    def test_calculate_price_change(self):
        # Gain
        abs_change, pct_change = calculate_price_change(Decimal("110.00"), Decimal("100.00"))
        self.assertEqual(abs_change, Decimal("10.0000"))
        self.assertEqual(pct_change, Decimal("10.0000"))

        # Loss
        abs_loss, pct_loss = calculate_price_change(Decimal("85.00"), Decimal("100.00"))
        self.assertEqual(abs_loss, Decimal("-15.0000"))
        self.assertEqual(pct_loss, Decimal("-15.0000"))

        # Zero previous price edge case
        abs_zero, pct_zero = calculate_price_change(Decimal("50.00"), Decimal("0.00"))
        self.assertEqual(abs_zero, Decimal("50.0000"))
        self.assertEqual(pct_zero, Decimal("0.0000"))

    def test_calculate_returns(self):
        prices = [Decimal("100.00"), Decimal("105.00"), Decimal("94.50")]
        returns = calculate_returns(prices)
        self.assertEqual(len(returns), 2)
        self.assertEqual(returns[0], Decimal("0.050000"))
        self.assertEqual(returns[1], Decimal("-0.100000"))

        # Edge cases: 0 or 1 price
        self.assertEqual(calculate_returns([]), [])
        self.assertEqual(calculate_returns([Decimal("100")]), [])

    def test_calculate_log_returns(self):
        prices = [Decimal("100.00"), Decimal("110.517092")]
        log_rets = calculate_log_returns(prices)
        self.assertEqual(len(log_rets), 1)
        # ln(110.517092 / 100) ≈ 0.1
        self.assertAlmostEqual(float(log_rets[0]), 0.10, places=4)

        # Handling of non-positive prices
        non_positive = [Decimal("100"), Decimal("-10"), Decimal("50")]
        safe_log = calculate_log_returns(non_positive)
        self.assertEqual(safe_log[0], Decimal("0.000000"))

    def test_calculate_period_return(self):
        times = [
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 2, tzinfo=timezone.utc),
            datetime(2026, 1, 3, tzinfo=timezone.utc),
        ]
        prices = [Decimal("100.00"), Decimal("110.00"), Decimal("125.00")]
        result = calculate_period_return(prices, timestamps=times)

        self.assertIsNotNone(result)
        self.assertEqual(result.start_price, Decimal("100.00"))
        self.assertEqual(result.end_price, Decimal("125.00"))
        self.assertEqual(result.absolute_change, Decimal("25.0000"))
        self.assertEqual(result.percentage_change, Decimal("25.0000"))
        self.assertEqual(result.start_time, times[0])
        self.assertEqual(result.end_time, times[-1])
        self.assertIsNotNone(result.log_return)

        # Insufficient data points
        self.assertIsNone(calculate_period_return([Decimal("100")]))

    def test_calculate_rolling_volatility(self):
        # 5 returns
        returns = [
            Decimal("0.01"),
            Decimal("-0.01"),
            Decimal("0.02"),
            Decimal("-0.02"),
            Decimal("0.00"),
        ]
        vol = calculate_rolling_volatility(returns, annualize_factor=252)
        self.assertGreater(vol.sample_std, Decimal("0"))
        self.assertGreater(vol.annualized_volatility, vol.sample_std)
        self.assertEqual(vol.annualize_factor, 252)
        self.assertEqual(vol.sample_count, 5)

        # Window limitation
        vol_win = calculate_rolling_volatility(returns, window=3)
        self.assertEqual(vol_win.sample_count, 3)

        # Insufficient sample
        vol_single = calculate_rolling_volatility([Decimal("0.01")])
        self.assertEqual(vol_single.sample_std, Decimal("0"))
        self.assertEqual(vol_single.annualized_volatility, Decimal("0"))

    def test_calculate_drawdowns(self):
        # Series with peak at 120 and trough at 90 (-30 / -25%)
        prices = [
            Decimal("100"),
            Decimal("120"),
            Decimal("105"),
            Decimal("90"),
            Decimal("115"),
            Decimal("125"),
        ]
        dd = calculate_drawdowns(prices)
        self.assertEqual(dd.peak_price, Decimal("120"))
        self.assertEqual(dd.trough_price, Decimal("90"))
        self.assertEqual(dd.max_drawdown_amount, Decimal("30.0000"))
        self.assertEqual(dd.max_drawdown_pct, Decimal("25.00"))
        self.assertEqual(dd.peak_index, 1)
        self.assertEqual(dd.trough_index, 3)
        self.assertTrue(dd.is_recovered)  # Last price 125 >= peak 120

        # Unrecovered series
        unrecovered_prices = [Decimal("100"), Decimal("150"), Decimal("80")]
        dd_unrec = calculate_drawdowns(unrecovered_prices)
        self.assertFalse(dd_unrec.is_recovered)
        self.assertEqual(dd_unrec.max_drawdown_amount, Decimal("70.0000"))

        # Empty series
        dd_empty = calculate_drawdowns([])
        self.assertEqual(dd_empty.max_drawdown_amount, Decimal("0"))

    def test_calculate_price_summary(self):
        prices = [Decimal("10"), Decimal("20"), Decimal("30"), Decimal("40"), Decimal("50")]
        summary = calculate_price_summary(prices)
        self.assertIsNotNone(summary)
        self.assertEqual(summary.current_price, Decimal("50"))
        self.assertEqual(summary.min_price, Decimal("10"))
        self.assertEqual(summary.max_price, Decimal("50"))
        self.assertEqual(summary.mean_price, Decimal("30.0000"))
        self.assertEqual(summary.median_price, Decimal("30.0000"))
        self.assertEqual(summary.data_points, 5)

        self.assertIsNone(calculate_price_summary([]))


if __name__ == "__main__":
    unittest.main()
