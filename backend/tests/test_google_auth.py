import unittest
from unittest.mock import AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.schemas.auth import RegisterRequest
from app.core.errors import AuthenticationError, ValidationError
from app.database.models import Base
from app.services.auth import AuthService
from app.services.google_auth import GoogleAuthService


class TestGoogleAuthService(unittest.IsolatedAsyncioTestCase):
    """Test suite covering Google OAuth 2.0 / OpenID Connect and safe account linking."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.google_service = GoogleAuthService(self.db)
        self.auth_service = AuthService(self.db)

    def tearDown(self):
        self.db.close()

    def test_generate_authorization_url_contains_pkce(self):
        """Verify generation of Google authorization URL with S256 code challenge."""
        data = self.google_service.generate_authorization_url()
        self.assertIn("accounts.google.com", data["auth_url"])
        self.assertIn("code_challenge=", data["auth_url"])
        self.assertIn("code_challenge_method=S256", data["auth_url"])
        self.assertTrue(len(data["state"]) > 20)
        self.assertTrue(len(data["code_verifier"]) > 40)

    async def test_state_mismatch_rejected(self):
        """Verify invalid or mismatched OAuth state parameter is rejected."""
        with self.assertRaises(ValidationError):
            await self.google_service.handle_callback(
                code="mock-code-alice",
                state="state_sent_to_google",
                expected_state="different_stored_state",
                code_verifier="mock_verifier",
            )

    async def test_new_user_registration_via_google(self):
        """Verify new user registration and session creation from verified Google identity."""
        user, session_token, csrf_token = await self.google_service.handle_callback(
            code="mock-code-alice",
            state="state123",
            expected_state="state123",
            code_verifier="verifier123",
            ip_address="192.168.1.5",
        )

        self.assertIsNotNone(user)
        self.assertEqual(user.email, "alice@gmail.com")
        self.assertTrue(user.email_verified_at)
        self.assertIsNone(user.password_hash)  # Google-only account
        self.assertTrue(len(session_token) > 20)

        # Login again with same Google identity
        user2, sess2, _ = await self.google_service.handle_callback(
            code="mock-code-alice",
            state="state456",
            expected_state="state456",
            code_verifier="verifier456",
        )
        self.assertEqual(user.id, user2.id)

    async def test_account_linking_protection_unauthenticated(self):
        """Verify matching email with password account is NOT silently linked without proof of ownership."""
        # Create user with local email/password
        self.auth_service.register(
            RegisterRequest(
                email="bob@gmail.com",
                password="BobSecretPassword123!",
                display_name="Bob Trader",
            )
        )

        # Unauthenticated Google sign-in with bob@gmail.com must fail
        with self.assertRaises(AuthenticationError) as ctx:
            await self.google_service.handle_callback(
                code="mock-code-bob",
                state="state789",
                expected_state="state789",
                code_verifier="verifier789",
                authenticated_user_id=None,  # Not currently authenticated
            )
        self.assertIn("Please sign in with your email and password first", str(ctx.exception))

    async def test_account_linking_authenticated_success(self):
        """Verify authenticated user can safely link their Google identity."""
        user, _ = self.auth_service.register(
            RegisterRequest(
                email="charlie@gmail.com",
                password="CharliePassword123!",
                display_name="Charlie",
            )
        )

        # Authenticated linking passing authenticated_user_id
        linked_user, sess, _ = await self.google_service.handle_callback(
            code="mock-code-charlie",
            state="state111",
            expected_state="state111",
            code_verifier="verifier111",
            authenticated_user_id=user.id,
        )
        self.assertEqual(linked_user.id, user.id)

        # Verify user now has both local and google identities
        identities = self.google_service.user_repo.get_identities_for_user(user.id)
        providers = {ident.provider for ident in identities}
        self.assertIn("local", providers)
        self.assertIn("google", providers)


if __name__ == "__main__":
    unittest.main()

