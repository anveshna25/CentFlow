from decimal import Decimal
import unittest

from app.analytics import (
    ATRResult,
    calculate_atr,
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
    calculate_true_range,
)


class TestAnalyticsIndicators(unittest.TestCase):
    """Test suite covering technical indicators calculation and edge cases."""

    def test_calculate_sma(self):
        prices = [Decimal("10"), Decimal("20"), Decimal("30"), Decimal("40"), Decimal("50")]

        # Window = 3: indices 0, 1 are None; index 2 is (10+20+30)/3 = 20; 3 is 30; 4 is 40
        sma3 = calculate_sma(prices, window=3)
        self.assertEqual(len(sma3), 5)
        self.assertIsNone(sma3[0])
        self.assertIsNone(sma3[1])
        self.assertEqual(sma3[2], Decimal("20.0000"))
        self.assertEqual(sma3[3], Decimal("30.0000"))
        self.assertEqual(sma3[4], Decimal("40.0000"))

        # Window = 1: each price itself
        sma1 = calculate_sma(prices, window=1)
        self.assertEqual(sma1, [Decimal("10.0000"), Decimal("20.0000"), Decimal("30.0000"), Decimal("40.0000"), Decimal("50.0000")])

        # Window > length
        sma10 = calculate_sma(prices, window=10)
        self.assertEqual(sma10, [None] * 5)

        # Empty
        self.assertEqual(calculate_sma([], window=5), [])

        # Invalid window
        with self.assertRaises(ValueError):
            calculate_sma(prices, window=0)

    def test_calculate_ema(self):
        prices = [Decimal("10"), Decimal("20"), Decimal("30"), Decimal("40"), Decimal("50")]

        # Window = 3:
        # alpha = 2 / (3 + 1) = 0.5
        # Index 0, 1 are None
        # Index 2 seed = SMA(10, 20, 30) = 20
        # Index 3 = 0.5 * 40 + 0.5 * 20 = 30
        # Index 4 = 0.5 * 50 + 0.5 * 30 = 40
        ema3 = calculate_ema(prices, window=3)
        self.assertEqual(len(ema3), 5)
        self.assertIsNone(ema3[0])
        self.assertIsNone(ema3[1])
        self.assertEqual(ema3[2], Decimal("20.0000"))
        self.assertEqual(ema3[3], Decimal("30.0000"))
        self.assertEqual(ema3[4], Decimal("40.0000"))

        # Length < window
        self.assertEqual(calculate_ema([Decimal("10")], window=5), [None])
        self.assertEqual(calculate_ema([], window=5), [])

        with self.assertRaises(ValueError):
            calculate_ema(prices, window=-1)

    def test_calculate_rsi(self):
        # 16 prices: gives 15 changes, enough for 14-period RSI
        # Constantly increasing prices -> all gains, no losses -> RSI = 100
        increasing = [Decimal(str(i * 10)) for i in range(1, 17)]
        rsi_inc = calculate_rsi(increasing, period=14)
        self.assertEqual(len(rsi_inc), 16)
        # First 14 are None (indices 0..13)
        for i in range(14):
            self.assertIsNone(rsi_inc[i])
        self.assertEqual(rsi_inc[14], Decimal("100.00"))
        self.assertEqual(rsi_inc[15], Decimal("100.00"))

        # Constantly decreasing prices -> RSI = 0
        decreasing = [Decimal(str(200 - i * 10)) for i in range(1, 17)]
        rsi_dec = calculate_rsi(decreasing, period=14)
        self.assertEqual(rsi_dec[14], Decimal("0.00"))
        self.assertEqual(rsi_dec[15], Decimal("0.00"))

        # Flat prices -> RSI = 50
        flat = [Decimal("100")] * 16
        rsi_flat = calculate_rsi(flat, period=14)
        self.assertEqual(rsi_flat[14], Decimal("50.00"))

        # Insufficient data
        short_prices = [Decimal("10"), Decimal("20"), Decimal("30")]
        self.assertEqual(calculate_rsi(short_prices, period=14), [None, None, None])
        self.assertEqual(calculate_rsi([], period=14), [])

        with self.assertRaises(ValueError):
            calculate_rsi(increasing, period=0)

    def test_calculate_rsi_wilder_values(self):
        # Standard textbook sequence of 15 prices (14 periods)
        prices = [
            Decimal("44.34"), Decimal("44.09"), Decimal("44.15"), Decimal("43.61"),
            Decimal("44.33"), Decimal("44.83"), Decimal("45.10"), Decimal("45.42"),
            Decimal("45.84"), Decimal("46.08"), Decimal("45.89"), Decimal("46.03"),
            Decimal("45.61"), Decimal("46.28"), Decimal("46.28"), Decimal("46.00"),
        ]
        rsi = calculate_rsi(prices, period=14)
        self.assertEqual(len(rsi), len(prices))
        self.assertIsNotNone(rsi[14])
        # For this sequence at bar 14, RSI is around 70.46
        self.assertGreater(rsi[14], Decimal("65.00"))
        self.assertLess(rsi[14], Decimal("75.00"))

    def test_calculate_macd(self):
        # Generate 40 rising and oscillating prices to warm up slow=26, signal=9
        prices = [Decimal(str(100 + i * 2 + (i % 3))) for i in range(40)]
        result = calculate_macd(prices, fast=12, slow=26, signal=9)

        self.assertEqual(len(result.macd_line), 40)
        self.assertEqual(len(result.signal_line), 40)
        self.assertEqual(len(result.histogram), 40)

        # Before slow - 1 (index 25), MACD should be None
        for i in range(25):
            self.assertIsNone(result.macd_line[i])
        self.assertIsNotNone(result.macd_line[25])

        # Signal line requires 9 valid MACD points: index 25 + 8 = 33
        for i in range(33):
            self.assertIsNone(result.signal_line[i])
            self.assertIsNone(result.histogram[i])
        self.assertIsNotNone(result.signal_line[33])
        self.assertIsNotNone(result.histogram[33])

        # Histogram is exactly MACD - Signal
        diff = (result.macd_line[35] - result.signal_line[35]).quantize(Decimal("0.0001"))
        self.assertEqual(result.histogram[35], diff)

        # Edge cases
        short_res = calculate_macd([Decimal("100")] * 5, fast=12, slow=26)
        self.assertEqual(short_res.macd_line, [None] * 5)

        empty_res = calculate_macd([])
        self.assertEqual(empty_res.macd_line, [])

        with self.assertRaises(ValueError):
            calculate_macd(prices, fast=26, slow=12)

    def test_calculate_bollinger_bands(self):
        # 25 prices
        prices = [Decimal(str(100 + i)) for i in range(25)]
        bb = calculate_bollinger_bands(prices, window=20, num_std=Decimal("2.0"))

        self.assertEqual(len(bb.middle_band), 25)
        self.assertEqual(len(bb.upper_band), 25)
        self.assertEqual(len(bb.lower_band), 25)
        self.assertEqual(len(bb.bandwidth), 25)
        self.assertEqual(len(bb.percent_b), 25)

        # Warmup: first 19 (0..18) are None
        for i in range(19):
            self.assertIsNone(bb.middle_band[i])
            self.assertIsNone(bb.upper_band[i])
            self.assertIsNone(bb.lower_band[i])

        # Index 19 is fully populated
        self.assertIsNotNone(bb.middle_band[19])
        self.assertIsNotNone(bb.upper_band[19])
        self.assertIsNotNone(bb.lower_band[19])

        # Upper > Middle > Lower
        self.assertGreater(bb.upper_band[19], bb.middle_band[19])
        self.assertGreater(bb.middle_band[19], bb.lower_band[19])

        # Bandwidth is positive
        self.assertGreater(bb.bandwidth[19], Decimal("0"))

        # %B is between 0 and 1 for prices inside the bands
        self.assertGreaterEqual(bb.percent_b[19], Decimal("0"))
        self.assertLessEqual(bb.percent_b[19], Decimal("1"))

        # Flat prices (zero volatility)
        flat = [Decimal("100")] * 22
        bb_flat = calculate_bollinger_bands(flat, window=20)
        self.assertEqual(bb_flat.upper_band[20], Decimal("100.0000"))
        self.assertEqual(bb_flat.lower_band[20], Decimal("100.0000"))
        self.assertEqual(bb_flat.bandwidth[20], Decimal("0.00"))
        self.assertEqual(bb_flat.percent_b[20], Decimal("0.5000"))

        # Empty and short
        empty_bb = calculate_bollinger_bands([])
        self.assertEqual(empty_bb.middle_band, [])

        short_bb = calculate_bollinger_bands([Decimal("100")] * 5, window=20)
        self.assertEqual(short_bb.middle_band, [None] * 5)

    def test_calculate_true_range(self):
        highs = [Decimal("50"), Decimal("55"), Decimal("48"), Decimal("45"), Decimal("50")]
        lows = [Decimal("40"), Decimal("48"), Decimal("38"), Decimal("41"), Decimal("44")]
        closes = [Decimal("45"), Decimal("52"), Decimal("40"), Decimal("43"), Decimal("48")]

        tr = calculate_true_range(highs, lows, closes)
        self.assertEqual(len(tr), 5)
        self.assertEqual(tr[0], Decimal("10.0000"))  # High - Low: 50 - 40 = 10
        self.assertEqual(tr[1], Decimal("10.0000"))  # max(55-48, 55-45, |48-45|) = 10
        self.assertEqual(tr[2], Decimal("14.0000"))  # gap down: max(48-38, |48-52|, |38-52|) = 14
        self.assertEqual(tr[3], Decimal("5.0000"))   # max(45-41, 45-40, |41-40|) = 5
        self.assertEqual(tr[4], Decimal("7.0000"))   # max(50-44, 50-43, |44-43|) = 7

        # Empty
        self.assertEqual(calculate_true_range([], [], []), [])

        # Length mismatch
        with self.assertRaises(ValueError):
            calculate_true_range([10], [5], [])

    def test_calculate_atr(self):
        highs = [Decimal("50"), Decimal("55"), Decimal("48"), Decimal("45"), Decimal("50")]
        lows = [Decimal("40"), Decimal("48"), Decimal("38"), Decimal("41"), Decimal("44")]
        closes = [Decimal("45"), Decimal("52"), Decimal("40"), Decimal("43"), Decimal("48")]

        # Period = 3
        atr_res = calculate_atr(highs, lows, closes, period=3)
        self.assertEqual(len(atr_res.atr), 5)
        self.assertIsNone(atr_res.atr[0])
        self.assertIsNone(atr_res.atr[1])

        # Seed ATR at index 2: SMA(10, 10, 14) = 34 / 3 = 11.3333
        self.assertEqual(atr_res.atr[2], Decimal("11.3333"))
        # ATR% at index 2: (11.3333 / 40) * 100 = 28.33%
        self.assertEqual(atr_res.atr_percent[2], Decimal("28.33"))

        # Subsequent periods smoothed with Wilder:
        # ATR_3 = (11.333333... * 2 + 5) / 3 = 9.2222
        self.assertEqual(atr_res.atr[3], Decimal("9.2222"))
        # ATR_4 = (9.222222... * 2 + 7) / 3 = 8.4815
        self.assertEqual(atr_res.atr[4], Decimal("8.4815"))

        # Period < 1 error
        with self.assertRaises(ValueError):
            calculate_atr(highs, lows, closes, period=0)

        # Length < period returns None
        short_res = calculate_atr(highs[:2], lows[:2], closes[:2], period=5)
        self.assertEqual(short_res.atr, [None, None])

        # Empty input
        empty_res = calculate_atr([], [], [], period=14)
        self.assertEqual(empty_res.atr, [])


if __name__ == "__main__":
    unittest.main()
