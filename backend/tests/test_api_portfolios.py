from decimal import Decimal
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.schemas.portfolio import PortfolioCreateRequest, PositionCreateRequest
from app.core.errors import NotFoundError, ValidationError
from app.database.models import Base
from app.database.session import get_db
from app.main import create_app
from app.repositories.portfolio import PortfolioRepository
from app.services.market_data import MarketDataService
from app.services.portfolio import PortfolioService


class TestPortfolioFoundationAndHoldings(unittest.IsolatedAsyncioTestCase):
    """Test suite covering PortfolioRepository, PortfolioService, and Portfolio API routes."""

    def setUp(self):
        # Create an isolated in-memory SQLite database with StaticPool
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = self.Session()

        self.market_data_service = MarketDataService(enable_cache=False)
        self.portfolio_repo = PortfolioRepository(self.db)
        self.portfolio_service = PortfolioService(
            db=self.db,
            market_data_service=self.market_data_service,
        )

        # Setup FastAPI TestClient with DB dependency override
        self.app = create_app()

        def override_get_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        self.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(self.app)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    async def test_list_portfolios_creates_default_when_empty(self):
        """Listing portfolios when none exist should automatically provision a default portfolio."""
        portfolios = await self.portfolio_service.list_portfolios()
        self.assertEqual(len(portfolios), 1)
        self.assertEqual(portfolios[0].name, "Main Multi-Asset")
        self.assertEqual(portfolios[0].total_valuation, Decimal("0.00"))
        self.assertEqual(portfolios[0].positions_count, 0)

    async def test_create_and_get_portfolio(self):
        """Creating and retrieving a portfolio by ID."""
        req = PortfolioCreateRequest(
            name="Macro Growth Fund",
            description="High-conviction equity and crypto holdings",
            base_currency="USD",
        )
        created = await self.portfolio_service.create_portfolio(req)
        self.assertIsNotNone(created.id)
        self.assertEqual(created.name, "Macro Growth Fund")
        self.assertEqual(created.base_currency, "USD")

        fetched = await self.portfolio_service.get_portfolio(created.id)
        self.assertEqual(fetched.id, created.id)
        self.assertEqual(fetched.name, "Macro Growth Fund")

    async def test_create_portfolio_blank_name_raises_error(self):
        """Portfolio with empty/whitespace name should fail validation."""
        req = PortfolioCreateRequest(name="   ", description="Invalid")
        with self.assertRaises(ValidationError):
            await self.portfolio_service.create_portfolio(req)

    async def test_get_unknown_portfolio_raises_not_found(self):
        """Looking up a nonexistent portfolio should raise NotFoundError."""
        with self.assertRaises(NotFoundError):
            await self.portfolio_service.get_portfolio("nonexistent-portfolio-id")

    async def test_add_and_accumulate_position(self):
        """Adding a position and accumulating additional units with weighted average price calculation."""
        # Provision a portfolio
        pf_req = PortfolioCreateRequest(name="Tech & Crypto", base_currency="USD")
        pf = await self.portfolio_service.create_portfolio(pf_req)

        # 1. Add first position in AAPL: 10 units @ $150.00
        pos1 = PositionCreateRequest(
            symbol="AAPL",
            quantity=Decimal("10"),
            average_price=Decimal("150.00"),
            currency="USD",
        )
        updated1 = await self.portfolio_service.add_position(pf.id, pos1)
        self.assertEqual(updated1.positions_count, 1)
        holding1 = updated1.positions[0]
        self.assertEqual(holding1.symbol, "AAPL")
        self.assertEqual(holding1.quantity, Decimal("10"))
        self.assertEqual(holding1.cost_basis, Decimal("1500.00"))
        # AAPL mock price is 185.50 -> market_value = 1855.00
        self.assertEqual(holding1.market_value, Decimal("1855.00"))
        self.assertEqual(holding1.unrealized_pnl, Decimal("355.00"))

        # 2. Accumulate more AAPL: 10 units @ $170.00
        # Weighted average entry should be (1500 + 1700) / 20 = $160.00
        pos2 = PositionCreateRequest(
            symbol="AAPL",
            quantity=Decimal("10"),
            average_price=Decimal("170.00"),
            currency="USD",
        )
        updated2 = await self.portfolio_service.add_position(pf.id, pos2)
        self.assertEqual(updated2.positions_count, 1)
        holding2 = updated2.positions[0]
        self.assertEqual(holding2.quantity, Decimal("20"))
        self.assertEqual(holding2.average_price, Decimal("160.000000"))
        self.assertEqual(holding2.cost_basis, Decimal("3200.00"))
        # 20 * 185.50 = 3710.00
        self.assertEqual(holding2.market_value, Decimal("3710.00"))
        self.assertEqual(holding2.unrealized_pnl, Decimal("510.00"))

    async def test_remove_position(self):
        """Removing an existing position updates aggregate portfolio valuations."""
        pf = await self.portfolio_service.create_portfolio(PortfolioCreateRequest(name="Hedging"))
        pos_req = PositionCreateRequest(symbol="SPY", quantity=Decimal("5"), average_price=Decimal("500.00"))
        updated = await self.portfolio_service.add_position(pf.id, pos_req)
        self.assertEqual(updated.positions_count, 1)
        pos_id = updated.positions[0].id

        after_delete = await self.portfolio_service.remove_position(pf.id, pos_id)
        self.assertEqual(after_delete.positions_count, 0)
        self.assertEqual(after_delete.total_valuation, Decimal("0.00"))

    async def test_position_live_market_data_valuations_and_daily_pnl(self):
        """Validates that live quotes properly update market_value, daily_pnl, and daily_pnl_percent."""
        pf = await self.portfolio_service.create_portfolio(PortfolioCreateRequest(name="Alpha Fund"))
        pos_req = PositionCreateRequest(
            symbol="AAPL",
            quantity=Decimal("10"),
            average_price=Decimal("150.00"),
            currency="USD",
        )
        updated = await self.portfolio_service.add_position(pf.id, pos_req)
        self.assertEqual(updated.positions_count, 1)

        holding = updated.positions[0]
        # In mock provider: AAPL price = 185.50, previous_close = 183.90, change = +1.60 (+0.87%)
        self.assertEqual(holding.current_price, Decimal("185.500000"))
        self.assertEqual(holding.market_value, Decimal("1855.00"))
        self.assertEqual(holding.cost_basis, Decimal("1500.00"))
        self.assertEqual(holding.unrealized_pnl, Decimal("355.00"))
        self.assertEqual(holding.unrealized_pnl_percent, Decimal("23.67"))
        self.assertEqual(holding.daily_pnl, Decimal("16.00"))
        self.assertEqual(holding.daily_pnl_percent, Decimal("0.87"))
        self.assertFalse(holding.is_stale)

        # Portfolio aggregate daily metrics
        self.assertEqual(updated.total_valuation, Decimal("1855.00"))
        self.assertEqual(updated.total_daily_pnl, Decimal("16.00"))
        self.assertEqual(updated.total_daily_pnl_percent, Decimal("0.87"))
        self.assertFalse(updated.is_stale)

    async def test_fallback_to_entry_price_when_symbol_unquoted(self):
        """Positions with unquoted or offline symbols fall back to entry price with is_stale=True."""
        pf = await self.portfolio_service.create_portfolio(PortfolioCreateRequest(name="Custom Assets"))
        pos_req = PositionCreateRequest(
            symbol="CUSTOM_ASSET_XYZ",
            quantity=Decimal("5"),
            average_price=Decimal("100.00"),
            currency="USD",
        )
        updated = await self.portfolio_service.add_position(pf.id, pos_req)
        holding = updated.positions[0]
        self.assertEqual(holding.current_price, Decimal("100.000000"))
        self.assertEqual(holding.market_value, Decimal("500.00"))
        self.assertEqual(holding.cost_basis, Decimal("500.00"))
        self.assertEqual(holding.unrealized_pnl, Decimal("0.00"))
        self.assertEqual(holding.daily_pnl, Decimal("0.00"))
        self.assertEqual(holding.daily_pnl_percent, Decimal("0.00"))
        self.assertTrue(holding.is_stale)
        self.assertTrue(updated.is_stale)

    async def test_multi_asset_portfolio_batch_valuation_consistency(self):
        """Batch quote aggregation ensures numerical consistency across diverse asset holdings."""
        pf = await self.portfolio_service.create_portfolio(PortfolioCreateRequest(name="Balanced Multi-Asset"))
        await self.portfolio_service.add_position(
            pf.id,
            PositionCreateRequest(symbol="AAPL", quantity=Decimal("10"), average_price=Decimal("150.00")),
        )
        await self.portfolio_service.add_position(
            pf.id,
            PositionCreateRequest(symbol="MSFT", quantity=Decimal("5"), average_price=Decimal("400.00")),
        )
        refreshed = await self.portfolio_service.get_portfolio(pf.id)
        self.assertEqual(refreshed.positions_count, 2)

        expected_valuation = sum(p.market_value for p in refreshed.positions)
        expected_cost = sum(p.cost_basis for p in refreshed.positions)
        expected_daily_pnl = sum(p.daily_pnl for p in refreshed.positions)

        self.assertEqual(refreshed.total_valuation, expected_valuation)
        self.assertEqual(refreshed.total_cost_basis, expected_cost)
        self.assertEqual(refreshed.total_daily_pnl, expected_daily_pnl)
        self.assertEqual(refreshed.total_unrealized_pnl, expected_valuation - expected_cost)

    def test_api_portfolios_endpoints_e2e(self):
        """End-to-end HTTP integration test for portfolios and position endpoints via TestClient."""
        # 1. List portfolios (default created)
        res = self.client.get("/api/v1/portfolios")
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertGreaterEqual(len(data), 1)
        pf_id = data[0]["id"]

        # 2. Add position in BTC-USD: 0.5 units @ $60,000.00
        add_pos_res = self.client.post(
            f"/api/v1/portfolios/{pf_id}/positions",
            json={
                "symbol": "BTC-USD",
                "quantity": 0.5,
                "average_price": 60000.00,
                "currency": "USD",
            },
        )
        self.assertEqual(add_pos_res.status_code, 201)
        pf_data = add_pos_res.json()["data"]
        self.assertEqual(pf_data["positions_count"], 1)
        position = pf_data["positions"][0]
        self.assertEqual(position["symbol"], "BTC-USD")
        self.assertEqual(float(position["cost_basis"]), 30000.00)
        # Mock price is 65,400.00 -> market value = 32,700.00
        self.assertEqual(float(position["market_value"]), 32700.00)
        self.assertEqual(float(position["unrealized_pnl"]), 2700.00)
        self.assertIn("daily_pnl", position)
        self.assertIn("daily_pnl_percent", position)
        self.assertIn("is_stale", position)
        self.assertIn("total_daily_pnl", pf_data)
        self.assertIn("total_daily_pnl_percent", pf_data)
        pos_id = position["id"]

        # 3. Retrieve portfolio detail
        get_res = self.client.get(f"/api/v1/portfolios/{pf_id}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["data"]["id"], pf_id)

        # 4. Delete position
        del_res = self.client.delete(f"/api/v1/portfolios/{pf_id}/positions/{pos_id}")
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(del_res.json()["data"]["positions_count"], 0)


if __name__ == "__main__":
    unittest.main()

