from datetime import datetime, timedelta, timezone
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.schemas.auth import LoginRequest, RegisterRequest
from app.core.errors import AuthenticationError, ConflictError, NotFoundError, ValidationError
from app.database.models import Base
from app.services.auth import AuthService


class TestAuthService(unittest.TestCase):
    """Test suite covering AuthService domain operations and security policies."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.auth_service = AuthService(self.db)

    def tearDown(self):
        self.db.close()

    def test_registration_success_and_duplicate_rejection(self):
        """Verify successful user registration and duplicate normalized email rejection."""
        req = RegisterRequest(
            email="Trader.One@CentFlow.com",
            password="SecurePassword123!",
            display_name="Trader One",
        )
        user, token = self.auth_service.register(req)

        self.assertIsNotNone(user.id)
        self.assertEqual(user.email_normalized, "trader.one@centflow.com")
        self.assertFalse(user.email_verified_at)
        self.assertTrue(len(token) > 20)

        # Attempt duplicate registration with different casing
        duplicate_req = RegisterRequest(
            email="trader.one@centflow.com",
            password="AnotherPassword456!",
            display_name="Trader One Duplicate",
        )
        with self.assertRaises(ConflictError):
            self.auth_service.register(duplicate_req)

    def test_login_success_and_invalid_credentials(self):
        """Verify password verification, session issuance, and rejection of bad credentials."""
        req = RegisterRequest(
            email="investor@centflow.com",
            password="CorrectPassword123!",
            display_name="Institutional Investor",
        )
        self.auth_service.register(req)

        # Successful login
        login_req = LoginRequest(email="investor@centflow.com", password="CorrectPassword123!")
        user, session_token, csrf_token = self.auth_service.login(login_req, ip_address="10.0.0.1")

        self.assertIsNotNone(user)
        self.assertTrue(len(session_token) > 20)
        self.assertTrue(len(csrf_token) > 20)

        # Verify session validates
        validated_user = self.auth_service.validate_session(session_token)
        self.assertIsNotNone(validated_user)
        self.assertEqual(validated_user.id, user.id)

        # Wrong password
        bad_req = LoginRequest(email="investor@centflow.com", password="WrongPassword999!")
        with self.assertRaises(AuthenticationError):
            self.auth_service.login(bad_req)

        # Nonexistent email
        ghost_req = LoginRequest(email="ghost@centflow.com", password="AnyPassword123!")
        with self.assertRaises(AuthenticationError):
            self.auth_service.login(ghost_req)

    def test_email_verification_lifecycle(self):
        """Verify email verification token redemption and single-use enforcement."""
        req = RegisterRequest(
            email="verify.me@centflow.com",
            password="ValidPassword123!",
            display_name="Verify Me",
        )
        user, token = self.auth_service.register(req)
        self.assertFalse(user.email_verified_at)

        # Redeem token
        verified_user = self.auth_service.verify_email(token)
        self.assertTrue(verified_user.email_verified_at)

        # Second redemption should fail (single use)
        with self.assertRaises(ValidationError):
            self.auth_service.verify_email(token)

        # Invalid token
        with self.assertRaises(ValidationError):
            self.auth_service.verify_email("invalid_token_string_xyz")

    def test_logout_revokes_session(self):
        """Verify that logging out invalidates session token immediately."""
        req = RegisterRequest(
            email="logout.user@centflow.com",
            password="ValidPassword123!",
            display_name="Logout User",
        )
        self.auth_service.register(req)

        login_req = LoginRequest(email="logout.user@centflow.com", password="ValidPassword123!")
        user, session_token, _ = self.auth_service.login(login_req)

        # Valid before logout
        self.assertIsNotNone(self.auth_service.validate_session(session_token))

        # Logout
        revoked = self.auth_service.logout(session_token)
        self.assertTrue(revoked)

        # Invalid after logout
        self.assertIsNone(self.auth_service.validate_session(session_token))

    def test_password_recovery_and_reset(self):
        """Verify password reset generates token and revokes all active sessions upon update."""
        req = RegisterRequest(
            email="recovery@centflow.com",
            password="OldPassword123!",
            display_name="Recovery User",
        )
        self.auth_service.register(req)

        # Login to create an active session
        login_req = LoginRequest(email="recovery@centflow.com", password="OldPassword123!")
        user, active_session_token, _ = self.auth_service.login(login_req)

        # Request reset
        reset_token = self.auth_service.request_password_reset("recovery@centflow.com")
        self.assertIsNotNone(reset_token)

        # Nonexistent email returns None silently (anti-enumeration)
        self.assertIsNone(self.auth_service.request_password_reset("nobody@centflow.com"))

        # Complete reset with new password
        success = self.auth_service.reset_password(reset_token, "NewPassword987!")
        self.assertTrue(success)

        # Old active session must now be invalidated
        self.assertIsNone(self.auth_service.validate_session(active_session_token))

        # Old password must fail
        with self.assertRaises(AuthenticationError):
            self.auth_service.login(LoginRequest(email="recovery@centflow.com", password="OldPassword123!"))

        # New password must succeed
        user2, new_session, _ = self.auth_service.login(
            LoginRequest(email="recovery@centflow.com", password="NewPassword987!")
        )
        self.assertIsNotNone(user2)

    def test_change_password_and_session_rotation(self):
        """Verify password change requires current password and rotates other sessions."""
        req = RegisterRequest(
            email="change.pw@centflow.com",
            password="InitialPassword123!",
            display_name="Change Password User",
        )
        user, _ = self.auth_service.register(req)

        # Create Session 1 and Session 2
        login_req = LoginRequest(email="change.pw@centflow.com", password="InitialPassword123!")
        _, sess1, _ = self.auth_service.login(login_req)
        _, sess2, _ = self.auth_service.login(login_req)

        self.assertIsNotNone(self.auth_service.validate_session(sess1))
        self.assertIsNotNone(self.auth_service.validate_session(sess2))

        # Change password from Session 2 (preserves sess2, revokes sess1)
        self.auth_service.change_password(
            user_id=user.id,
            current_password="InitialPassword123!",
            new_password="UpdatedPassword567!",
            current_session_token=sess2,
        )

        # Sess 1 is revoked; Sess 2 remains valid
        self.assertIsNone(self.auth_service.validate_session(sess1))
        self.assertIsNotNone(self.auth_service.validate_session(sess2))

        # Wrong current password fails
        with self.assertRaises(AuthenticationError):
            self.auth_service.change_password(
                user_id=user.id,
                current_password="WrongCurrentPassword!",
                new_password="AnotherPassword!",
            )


if __name__ == "__main__":
    unittest.main()

