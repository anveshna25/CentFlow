from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.analytics import (
    MomentumState,
    TrendPosture,
    VolatilityRegime,
    synthesize_market_intelligence,
)
from app.database.models import Base
from app.providers.base import ProviderBar, ProviderInstrument
from app.repositories.asset import AssetRepository
from app.repositories.exchange import ExchangeRepository
from app.repositories.instrument import InstrumentRepository
from app.repositories.price import PriceRepository
from app.services.analytics import AnalyticsService
from app.services.market_data import MarketDataService


class TestAnalyticsServiceAndIntelligence(unittest.IsolatedAsyncioTestCase):
    """Test suite covering AnalyticsService and deterministic market intelligence synthesis."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = self.Session()

        self.instrument_repo = InstrumentRepository(self.db)
        self.price_repo = PriceRepository(self.db)

        self.market_data_service = MarketDataService(enable_cache=False)
        self.analytics_service = AnalyticsService(
            market_data_service=self.market_data_service,
            db=self.db,
        )


    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_synthesize_intelligence_empty(self):
        summary = synthesize_market_intelligence("AAPL", [])
        self.assertEqual(summary.symbol, "AAPL")
        self.assertEqual(summary.current_price, Decimal("0"))
        self.assertEqual(summary.composite_score, 50)
        self.assertEqual(summary.trend_posture, TrendPosture.NEUTRAL)
        self.assertEqual(summary.summary_verdict, "Insufficient Data")

    def test_synthesize_intelligence_strong_bullish(self):
        # 210 steadily ascending bars
        base = 100.0
        prices = [Decimal(str(round(base + i * 1.5, 2))) for i in range(210)]
        times = [datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=i) for i in range(210)]

        summary = synthesize_market_intelligence("AAPL", prices, timestamps=times)
        self.assertEqual(summary.symbol, "AAPL")
        self.assertEqual(summary.trend_posture, TrendPosture.BULLISH)
        self.assertGreaterEqual(summary.composite_score, 65)
        self.assertIn("Bullish", summary.summary_verdict)
        self.assertGreater(len(summary.rationales), 0)
        self.assertIn("metrics", dir(summary))
        self.assertIsNotNone(summary.metrics["sma20"])
        self.assertIsNotNone(summary.metrics["sma50"])
        self.assertIsNotNone(summary.metrics["sma200"])

    def test_synthesize_intelligence_strong_bearish(self):
        # 210 steadily descending bars
        base = 400.0
        prices = [Decimal(str(round(base - i * 1.2, 2))) for i in range(210)]
        summary = synthesize_market_intelligence("TSLA", prices)
        self.assertEqual(summary.trend_posture, TrendPosture.BEARISH)
        self.assertLessEqual(summary.composite_score, 35)
        self.assertIn("Bearish", summary.summary_verdict)

    def test_synthesize_intelligence_volatility_regimes(self):
        # Low volatility: constant small oscillation around 100
        low_vol_prices = [Decimal(str(100 + (i % 2) * 0.1)) for i in range(50)]
        summary_low = synthesize_market_intelligence("BOND", low_vol_prices)
        self.assertEqual(summary_low.volatility_regime, VolatilityRegime.LOW)

        # High volatility: wild 10% swings every day
        high_vol_prices = [Decimal(str(100 * (1.10 if i % 2 == 0 else 0.90))) for i in range(50)]
        summary_high = synthesize_market_intelligence("CRYPTO", high_vol_prices)
        self.assertIn(summary_high.volatility_regime, [VolatilityRegime.HIGH, VolatilityRegime.EXTREME])

    async def test_analytics_service_orchestration_with_mock_provider(self):
        # By default MarketDataService uses mock provider with AAPL history
        summary = await self.analytics_service.get_price_summary("AAPL", lookback_days=30)
        self.assertIsNotNone(summary)
        self.assertGreater(summary.current_price, Decimal("0"))
        self.assertGreater(summary.data_points, 0)

        perf = await self.analytics_service.get_performance_metrics("AAPL", lookback_days=30)
        self.assertEqual(perf["symbol"], "AAPL")
        self.assertIsNotNone(perf["period_return"])
        self.assertIsNotNone(perf["volatility"])
        self.assertIsNotNone(perf["drawdown"])
        self.assertIsNotNone(perf["risk_metrics"])
        self.assertGreater(perf["risk_metrics"].win_rate, Decimal("0"))

        perf_bench = await self.analytics_service.get_performance_metrics(
            "AAPL",
            lookback_days=30,
            benchmark_symbol="SPY",
            risk_free_rate=0.04,
        )
        self.assertIsNotNone(perf_bench["benchmark"])
        self.assertEqual(perf_bench["benchmark"].benchmark_symbol, "SPY")
        self.assertIsNotNone(perf_bench["benchmark"].beta)
        self.assertIsNotNone(perf_bench["benchmark"].tracking_error)

        indicators = await self.analytics_service.get_technical_indicators(
            "AAPL",
            lookback_days=30,
            sma_windows=[5, 10],
            ema_windows=[5, 10],
        )
        self.assertIn("sma_5", indicators["smas"])
        self.assertIn("sma_10", indicators["smas"])
        self.assertIn("ema_5", indicators["emas"])
        self.assertIsNotNone(indicators["rsi"])
        self.assertIsNotNone(indicators["macd"])
        self.assertIsNotNone(indicators["bollinger"])

        intel = await self.analytics_service.get_market_intelligence("AAPL", lookback_days=30)
        self.assertEqual(intel.symbol, "AAPL")
        self.assertIsInstance(intel.composite_score, int)
        self.assertGreaterEqual(intel.composite_score, 0)
        self.assertLessEqual(intel.composite_score, 100)
        self.assertGreater(len(intel.rationales), 0)

    async def test_analytics_service_uses_database_persisted_prices(self):
        # Pre-populate database with 15 price bars for MSFT
        provider_inst = ProviderInstrument(
            symbol="MSFT",
            name="Microsoft Corporation",
            asset_type="equity",
            currency="USD",
            exchange="NASDAQ",
        )
        instrument = self.instrument_repo.get_or_create_from_provider(provider_inst)
        price_repo = PriceRepository(self.db)


        now = datetime.now(timezone.utc)
        bars = [
            ProviderBar(
                symbol="MSFT",
                timestamp=now - timedelta(days=15 - i),
                open=Decimal(str(300 + i)),
                high=Decimal(str(305 + i)),
                low=Decimal(str(295 + i)),
                close=Decimal(str(302 + i)),
                volume=1000000,
            )
            for i in range(15)
        ]
        price_repo.bulk_insert_bars(instrument.id, bars, currency="USD", interval="1d")

        # Query via AnalyticsService with DB

        prices, timestamps = await self.analytics_service.get_price_series("MSFT", lookback_days=30)
        self.assertEqual(len(prices), 15)
        self.assertEqual(prices[-1], Decimal("316.0000"))
        self.assertEqual(len(timestamps), 15)

        summary = await self.analytics_service.get_price_summary("MSFT", lookback_days=30)
        self.assertIsNotNone(summary)
        self.assertEqual(summary.data_points, 15)


if __name__ == "__main__":
    unittest.main()
