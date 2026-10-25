from decimal import Decimal
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


from app.api.routes.analytics import (
    get_analytics_service,
    get_analytics_summary,
    get_indicators,
    get_returns_analysis,
)
from app.api.schemas.base import ResponseEnvelope
from app.database.models import Base
from app.database.session import get_db
from app.main import create_app
from app.services.analytics import AnalyticsService
from app.services.market_data import MarketDataService



class TestAnalyticsApiRoutes(unittest.IsolatedAsyncioTestCase):
    """Test suite covering Analytics API route handlers and ResponseEnvelope structures."""

    async def asyncSetUp(self):
        self.market_data_service = MarketDataService(enable_cache=False)
        self.service = AnalyticsService(market_data_service=self.market_data_service)

    async def test_get_analytics_summary_route(self):
        envelope = await get_analytics_summary(symbol="AAPL", lookback_days=30, service=self.service)
        self.assertIsInstance(envelope, ResponseEnvelope)
        self.assertEqual(envelope.data.symbol, "AAPL")
        self.assertGreater(envelope.data.current_price, Decimal("0"))
        self.assertIsInstance(envelope.data.composite_score, int)
        self.assertGreater(len(envelope.data.rationales), 0)
        self.assertEqual(envelope.meta["symbol"], "AAPL")

    async def test_get_indicators_route(self):
        envelope = await get_indicators(
            symbol="AAPL",
            lookback_days=30,
            include_rsi=True,
            include_macd=True,
            include_bollinger=True,
            service=self.service,
        )
        self.assertIsInstance(envelope, ResponseEnvelope)
        self.assertEqual(envelope.data.symbol, "AAPL")
        self.assertGreater(len(envelope.data.prices), 0)
        self.assertIn("sma_20", envelope.data.smas)
        self.assertIsNotNone(envelope.data.macd)
        self.assertIsNotNone(envelope.data.bollinger)
        self.assertIsNotNone(envelope.data.rsi)

    async def test_get_returns_analysis_route(self):
        envelope = await get_returns_analysis(symbol="AAPL", lookback_days=30, service=self.service)
        self.assertIsInstance(envelope, ResponseEnvelope)
        self.assertEqual(envelope.data.symbol, "AAPL")
        self.assertIsNotNone(envelope.data.period_return)
        self.assertIsNotNone(envelope.data.volatility)
        self.assertIsNotNone(envelope.data.drawdown)
        self.assertIsNotNone(envelope.data.summary)


class TestAnalyticsHttpIntegration(unittest.TestCase):
    """HTTP integration tests verifying OpenAPI docs and endpoints mounted via TestClient."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        Base.metadata.create_all(bind=self.engine)
        self.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        self.app = create_app()

        def override_get_db():
            db = self.TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        self.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_analytics_endpoints_in_openapi_schema(self):
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()
        paths = schema.get("paths", {})
        self.assertIn("/api/v1/analytics/summary/{symbol}", paths)
        self.assertIn("/api/v1/analytics/indicators/{symbol}", paths)
        self.assertIn("/api/v1/analytics/returns/{symbol}", paths)

    def test_http_get_summary_endpoint(self):
        response = self.client.get("/api/v1/analytics/summary/AAPL?lookback_days=30")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("data", payload)
        self.assertIn("meta", payload)
        data = payload["data"]
        self.assertEqual(data["symbol"], "AAPL")
        self.assertIn("composite_score", data)
        self.assertIn("trend_posture", data)
        self.assertIn("momentum_state", data)
        self.assertIn("volatility_regime", data)

    def test_http_get_indicators_endpoint(self):
        response = self.client.get("/api/v1/analytics/indicators/AAPL?lookback_days=30")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        data = payload["data"]
        self.assertEqual(data["symbol"], "AAPL")
        self.assertIn("prices", data)
        self.assertIn("smas", data)
        self.assertIn("macd", data)
        self.assertIn("bollinger", data)

    def test_http_get_returns_endpoint(self):
        response = self.client.get("/api/v1/analytics/returns/AAPL?lookback_days=30")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        data = payload["data"]
        self.assertEqual(data["symbol"], "AAPL")
        self.assertIn("period_return", data)
        self.assertIn("volatility", data)
        self.assertIn("drawdown", data)


if __name__ == "__main__":
    unittest.main()
