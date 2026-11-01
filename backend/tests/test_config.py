import os
import unittest
from app.core.config import Settings, get_settings


class TestSettingsAndSecurityConfig(unittest.TestCase):
    """Test suite verifying application configuration and authentication security settings."""

    def test_default_security_settings(self):
        """Verify default identity and session security parameters."""
        settings = get_settings()
        self.assertEqual(settings.session_cookie_name, "centflow_session")
        self.assertEqual(settings.session_cookie_ttl_days, 7)
        self.assertEqual(settings.session_cookie_samesite, "lax")
        self.assertEqual(settings.csrf_cookie_name, "centflow_csrf")
        self.assertTrue(len(settings.session_secret_key) > 10)
        self.assertEqual(settings.frontend_base_url, "http://localhost:5173")

    def test_explicit_settings_instantiation(self):
        """Verify custom Settings instantiation with production security parameters."""
        custom = Settings(
            app_name="CentFlowProd",
            app_env="production",
            app_host="0.0.0.0",
            app_port=8080,
            database_url="sqlite:///prod.db",
            session_secret_key="production-super-secret-key-entropy-high",
            session_cookie_secure=True,
            session_cookie_ttl_days=14,
            google_client_id="mock-client-id.apps.googleusercontent.com",
            google_client_secret="mock-client-secret",
        )
        self.assertEqual(custom.app_env, "production")
        self.assertTrue(custom.session_cookie_secure)
        self.assertEqual(custom.session_cookie_ttl_days, 14)
        self.assertEqual(custom.google_client_id, "mock-client-id.apps.googleusercontent.com")


if __name__ == "__main__":
    unittest.main()

