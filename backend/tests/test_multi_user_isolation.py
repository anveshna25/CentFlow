import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.models import Base
from app.database.session import get_db
from app.main import create_app


class TestMultiUserIsolation(unittest.TestCase):
    """Test suite strictly validating cross-user data isolation and horizontal authorization."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

        self.app = create_app()

        def override_get_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        self.app.dependency_overrides[get_db] = override_get_db

        # Create Client for User A
        self.client_a = TestClient(self.app)
        self.client_a.post(
            "/api/v1/auth/register",
            json={
                "email": "user.a@centflow.com",
                "password": "PasswordUserA123!",
                "display_name": "User Alpha",
            },
        )
        login_a = self.client_a.post(
            "/api/v1/auth/login",
            json={"email": "user.a@centflow.com", "password": "PasswordUserA123!"},
        )
        self.csrf_a = login_a.cookies["centflow_csrf"]

        # Create Client for User B
        self.client_b = TestClient(self.app)
        self.client_b.post(
            "/api/v1/auth/register",
            json={
                "email": "user.b@centflow.com",
                "password": "PasswordUserB123!",
                "display_name": "User Beta",
            },
        )
        login_b = self.client_b.post(
            "/api/v1/auth/login",
            json={"email": "user.b@centflow.com", "password": "PasswordUserB123!"},
        )
        self.csrf_b = login_b.cookies["centflow_csrf"]

        # Unauthenticated Client
        self.client_unauthed = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()

    def test_unauthenticated_requests_rejected_with_401(self):
        """Verify unauthenticated requests cannot access portfolios or watchlists."""
        resp1 = self.client_unauthed.get("/api/v1/portfolios")
        self.assertEqual(resp1.status_code, 401)

        resp2 = self.client_unauthed.get("/api/v1/watchlists")
        self.assertEqual(resp2.status_code, 401)

    def test_portfolio_isolation_between_users(self):
        """User A creates a portfolio; User B cannot read, mutate, or delete it."""
        # 1. User A creates custom portfolio
        create_resp = self.client_a.post(
            "/api/v1/portfolios",
            json={
                "name": "Alpha Secret Portfolio",
                "description": "Proprietary trading fund",
                "base_currency": "USD",
            },
            headers={"X-CSRF-Token": self.csrf_a},
        )
        self.assertEqual(create_resp.status_code, 201)
        portfolio_a_id = create_resp.json()["data"]["id"]

        # 2. User A adds a position
        add_pos_resp = self.client_a.post(
            f"/api/v1/portfolios/{portfolio_a_id}/positions",
            json={
                "symbol": "AAPL",
                "quantity": 50,
                "average_price": 175.50,
                "currency": "USD",
            },
            headers={"X-CSRF-Token": self.csrf_a},
        )
        self.assertEqual(add_pos_resp.status_code, 201)

        # 3. User B lists portfolios -> MUST NOT contain Alpha Secret Portfolio
        list_b = self.client_b.get("/api/v1/portfolios")
        self.assertEqual(list_b.status_code, 200)
        user_b_portfolios = list_b.json()["data"]
        user_b_pf_ids = [p["id"] for p in user_b_portfolios]
        self.assertNotIn(portfolio_a_id, user_b_pf_ids)

        # 4. User B attempts direct GET of User A's portfolio -> 404 (Anti-Enumeration)
        direct_get_b = self.client_b.get(f"/api/v1/portfolios/{portfolio_a_id}")
        self.assertEqual(direct_get_b.status_code, 404)

        # 5. User B attempts adding position to User A's portfolio -> 404
        tamper_pos_b = self.client_b.post(
            f"/api/v1/portfolios/{portfolio_a_id}/positions",
            json={
                "symbol": "MSFT",
                "quantity": 100,
                "average_price": 400.0,
                "currency": "USD",
            },
            headers={"X-CSRF-Token": self.csrf_b},
        )
        self.assertEqual(tamper_pos_b.status_code, 404)

        # 6. User B attempts to delete User A's portfolio -> 404
        tamper_del_b = self.client_b.delete(
            f"/api/v1/portfolios/{portfolio_a_id}",
            headers={"X-CSRF-Token": self.csrf_b},
        )
        self.assertEqual(tamper_del_b.status_code, 404)

        # 7. User A's portfolio remains intact
        check_a = self.client_a.get(f"/api/v1/portfolios/{portfolio_a_id}")
        self.assertEqual(check_a.status_code, 200)
        self.assertEqual(check_a.json()["data"]["name"], "Alpha Secret Portfolio")

    def test_watchlist_isolation_between_users(self):
        """User A creates a watchlist; User B cannot read, mutate, or delete it."""
        # 1. User A creates custom watchlist
        wl_create_resp = self.client_a.post(
            "/api/v1/watchlists",
            json={
                "name": "Alpha Watchlist",
                "description": "Confidential tech assets",
            },
            headers={"X-CSRF-Token": self.csrf_a},
        )
        self.assertEqual(wl_create_resp.status_code, 201)
        wl_a_id = wl_create_resp.json()["data"]["id"]

        # 2. User A adds symbol to watchlist
        add_sym_resp = self.client_a.post(
            f"/api/v1/watchlists/{wl_a_id}/items",
            json={"symbol": "BTC-USD"},
            headers={"X-CSRF-Token": self.csrf_a},
        )
        self.assertEqual(add_sym_resp.status_code, 200)

        # 3. User B lists watchlists -> MUST NOT contain Alpha Watchlist
        list_b = self.client_b.get("/api/v1/watchlists")
        self.assertEqual(list_b.status_code, 200)
        b_watchlist_ids = [w["id"] for w in list_b.json()["data"]]
        self.assertNotIn(wl_a_id, b_watchlist_ids)

        # 4. User B attempts direct GET of User A's watchlist -> 404
        direct_b = self.client_b.get(f"/api/v1/watchlists/{wl_a_id}")
        self.assertEqual(direct_b.status_code, 404)

        # 5. User B attempts adding symbol to User A's watchlist -> 404
        tamper_item = self.client_b.post(
            f"/api/v1/watchlists/{wl_a_id}/items",
            json={"symbol": "NVDA"},
            headers={"X-CSRF-Token": self.csrf_b},
        )
        self.assertEqual(tamper_item.status_code, 404)

        # 6. User B attempts to delete User A's watchlist -> 404
        tamper_del_wl = self.client_b.delete(
            f"/api/v1/watchlists/{wl_a_id}",
            headers={"X-CSRF-Token": self.csrf_b},
        )
        self.assertEqual(tamper_del_wl.status_code, 404)


if __name__ == "__main__":
    unittest.main()

