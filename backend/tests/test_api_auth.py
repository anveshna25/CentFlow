import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.models import Base
from app.database.session import get_db
from app.main import create_app


class TestAuthApiRoutes(unittest.TestCase):
    """Integration test suite covering /api/v1/auth endpoints, cookies, and CSRF protection."""

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
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()

    def test_registration_and_login_lifecycle_with_cookies(self):
        """Verify registration, login setting HttpOnly cookie, /me introspection, and logout."""
        # 1. Register
        reg_resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "investor.pro@centflow.com",
                "password": "Password123!456",
                "display_name": "Pro Investor",
            },
        )
        self.assertEqual(reg_resp.status_code, 201)
        reg_data = reg_resp.json()
        self.assertIn("data", reg_data)
        self.assertEqual(reg_data["data"]["user"]["email"], "investor.pro@centflow.com")

        # 2. Login
        login_resp = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "investor.pro@centflow.com",
                "password": "Password123!456",
            },
        )
        self.assertEqual(login_resp.status_code, 200)

        # Check cookies
        cookies = login_resp.cookies
        self.assertIn("centflow_session", cookies)
        self.assertIn("centflow_csrf", cookies)

        csrf_token = cookies["centflow_csrf"]

        # 3. GET /me with session cookie
        me_resp = self.client.get("/api/v1/auth/me")
        self.assertEqual(me_resp.status_code, 200)
        self.assertEqual(me_resp.json()["data"]["email"], "investor.pro@centflow.com")

        # 4. GET /me without cookies should return 401
        unauthed_client = TestClient(self.app)
        unauthed_resp = unauthed_client.get("/api/v1/auth/me")
        self.assertEqual(unauthed_resp.status_code, 401)

        # 5. CSRF protection on mutating change-password
        # Missing CSRF header fails
        no_csrf_resp = self.client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "Password123!456",
                "new_password": "NewSecurePassword789!",
            },
        )
        self.assertEqual(no_csrf_resp.status_code, 400)

        # Valid CSRF header succeeds
        valid_change_resp = self.client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "Password123!456",
                "new_password": "NewSecurePassword789!",
            },
            headers={"X-CSRF-Token": csrf_token},
        )
        self.assertEqual(valid_change_resp.status_code, 200)

        # 6. Logout
        logout_resp = self.client.post("/api/v1/auth/logout")
        self.assertEqual(logout_resp.status_code, 200)

        # Subsequent /me fails
        after_logout_resp = self.client.get("/api/v1/auth/me")
        self.assertEqual(after_logout_resp.status_code, 401)

    def test_list_and_revoke_sessions(self):
        """Verify inspecting active sessions and revoking a specific session."""
        self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "session.tester@centflow.com",
                "password": "Password123!456",
                "display_name": "Session Tester",
            },
        )
        login_resp = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "session.tester@centflow.com",
                "password": "Password123!456",
            },
        )
        csrf_token = login_resp.cookies["centflow_csrf"]

        sess_resp = self.client.get("/api/v1/auth/sessions")
        self.assertEqual(sess_resp.status_code, 200)
        sessions = sess_resp.json()["data"]
        self.assertEqual(len(sessions), 1)
        self.assertTrue(sessions[0]["is_current"])

        # Revoke session
        session_id = sessions[0]["id"]
        del_resp = self.client.delete(
            f"/api/v1/auth/sessions/{session_id}",
            headers={"X-CSRF-Token": csrf_token},
        )
        self.assertEqual(del_resp.status_code, 200)

        # Now /me fails because session was revoked
        me_resp = self.client.get("/api/v1/auth/me")
        self.assertEqual(me_resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()

