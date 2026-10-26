from datetime import datetime, timezone
from decimal import Decimal
import unittest

from app.analytics import (
    align_price_series,
    calculate_benchmark_metrics,
    calculate_downside_deviation,
    calculate_drawdowns,
    calculate_log_returns,
    calculate_period_return,
    calculate_price_change,
    calculate_price_summary,
    calculate_returns,
    calculate_risk_adjusted_metrics,
    calculate_rolling_volatility,
    prepare_validated_series,
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

    def test_prepare_validated_series(self):
        t0 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 3, 0, 0, tzinfo=timezone.utc)

        # Out-of-order with duplicate timestamp and zero/negative prices
        raw_prices = [Decimal("100"), Decimal("0"), Decimal("-5"), Decimal("110"), Decimal("105")]
        raw_times = [t1, t0, t1, t2, t1]  # t1 has 100 then 105

        clean_p, clean_t = prepare_validated_series(raw_prices, raw_times)
        self.assertEqual(len(clean_p), 2)
        # Should be t1=105, t2=110 (t0 had 0, -5 was filtered, t1 was deduped to 105)
        self.assertEqual(clean_t, [t1, t2])
        self.assertEqual(clean_p, [Decimal("105"), Decimal("110")])

        # Empty handling
        empty_p, empty_t = prepare_validated_series([])
        self.assertEqual(empty_p, [])
        self.assertEqual(empty_t, [])

    def test_calculate_downside_deviation(self):
        # All positive returns -> downside deviation should be 0.0
        pos_rets = [Decimal("0.02"), Decimal("0.03"), Decimal("0.01")]
        self.assertEqual(calculate_downside_deviation(pos_rets), Decimal("0.000000"))

        # Returns with negative swings
        mixed_rets = [Decimal("0.05"), Decimal("-0.03"), Decimal("-0.02"), Decimal("0.04")]
        downside = calculate_downside_deviation(mixed_rets, annualize_factor=252)
        self.assertGreater(downside, Decimal("0"))

    def test_calculate_risk_adjusted_metrics(self):
        prices = [Decimal(str(100 + i * 2)) for i in range(30)]
        returns = calculate_returns(prices)
        vol = calculate_rolling_volatility(returns, annualize_factor=252)
        dd = calculate_drawdowns(prices)

        risk = calculate_risk_adjusted_metrics(
            prices=prices,
            returns=returns,
            volatility=vol,
            drawdown=dd,
            risk_free_rate=0.03,
            annualize_factor=252,
        )
        self.assertGreater(risk.annualized_return, Decimal("0"))
        self.assertGreater(risk.cagr, Decimal("0"))
        self.assertIsNotNone(risk.sharpe_ratio)
        self.assertGreater(risk.sharpe_ratio, Decimal("0"))
        self.assertEqual(risk.win_rate, Decimal("100.00"))
        self.assertEqual(risk.positive_periods, 29)
        self.assertEqual(risk.negative_periods, 0)

        # Empty edge case
        empty_risk = calculate_risk_adjusted_metrics([], [], vol, dd)
        self.assertIsNone(empty_risk.sharpe_ratio)
        self.assertEqual(empty_risk.total_periods, 0)

    def test_align_price_series_and_benchmark_metrics(self):
        t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 2, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 3, tzinfo=timezone.utc)
        t3 = datetime(2026, 1, 4, tzinfo=timezone.utc)
        t4 = datetime(2026, 1, 5, tzinfo=timezone.utc)

        # Asset traded on t0, t1, t3, t4 (e.g. holiday on t2)
        asset_p = [Decimal("100"), Decimal("105"), Decimal("110"), Decimal("115")]
        asset_t = [t0, t1, t3, t4]

        # Benchmark traded on t0, t1, t2, t3, t4
        bench_p = [Decimal("400"), Decimal("410"), Decimal("415"), Decimal("420"), Decimal("430")]
        bench_t = [t0, t1, t2, t3, t4]

        aligned_a, aligned_b, aligned_t = align_price_series(asset_p, asset_t, bench_p, bench_t)
        self.assertEqual(len(aligned_a), 4)  # t0, t1, t3, t4 intersect
        self.assertEqual(aligned_t, [t0, t1, t3, t4])
        self.assertEqual(aligned_b, [Decimal("400"), Decimal("410"), Decimal("420"), Decimal("430")])

        # Benchmark metrics calculation
        bm = calculate_benchmark_metrics(
            benchmark_symbol="SPY",
            asset_prices=aligned_a,
            benchmark_prices=aligned_b,
            annualize_factor=252,
        )
        self.assertEqual(bm.benchmark_symbol, "SPY")
        self.assertEqual(bm.aligned_periods, 3)
        self.assertIsNotNone(bm.beta)
        self.assertGreater(bm.beta, Decimal("0"))
        self.assertIsNotNone(bm.correlation)
        self.assertGreater(bm.correlation, Decimal("0.5"))
        self.assertIsNotNone(bm.tracking_error)


if __name__ == "__main__":
    unittest.main()

