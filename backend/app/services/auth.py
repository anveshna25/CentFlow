from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.api.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    SessionResponse,
    UserIdentityResponse,
    UserResponse,
)
from app.core.config import get_settings
from app.core.errors import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.security import (
    generate_csrf_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    needs_rehash,
    normalize_email,
    verify_password,
)
from app.database.models.user import UserModel
from app.repositories.email_token import EmailTokenRepository
from app.repositories.session import UserSessionRepository
from app.repositories.user import UserRepository


class AuthService:
    """Core domain service for user authentication, password management, and sessions."""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.session_repo = UserSessionRepository(db)
        self.email_token_repo = EmailTokenRepository(db)
        self.settings = get_settings()

    def register(self, request: RegisterRequest) -> tuple[UserModel, str]:
        """Register a new user account with normalized email, Argon2id hash, and local identity."""
        try:
            norm_email = normalize_email(request.email)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        existing = self.user_repo.get_by_email_normalized(norm_email)
        if existing:
            raise ConflictError("An account with this email address already exists.")

        pwd_hash = hash_password(request.password)
        user = self.user_repo.create_user(
            email=request.email.strip(),
            email_normalized=norm_email,
            display_name=request.display_name.strip(),
            password_hash=pwd_hash,
            is_active=True,
            email_verified=False,
        )

        # Link primary local identity
        self.user_repo.link_identity(
            user_id=user.id,
            provider="local",
            provider_subject=user.id,
            provider_email=norm_email,
        )

        # Create single-use verification token valid for 24 hours
        raw_verify_token = generate_opaque_token(32)
        token_hash = hash_token(raw_verify_token)
        now = datetime.now(timezone.utc)
        self.email_token_repo.create_token(
            user_id=user.id,
            token_hash=token_hash,
            token_type="VERIFY_EMAIL",
            expires_at=now + timedelta(hours=24),
        )

        return user, raw_verify_token

    def login(
        self,
        request: LoginRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> tuple[UserModel, str, str]:
        """Authenticate user credentials and issue an opaque server-managed session."""
        try:
            norm_email = normalize_email(request.email)
        except ValueError:
            raise AuthenticationError("Invalid email or password.")

        user = self.user_repo.get_by_email_normalized(norm_email)
        if not user or not user.is_active:
            raise AuthenticationError("Invalid email or password.")

        if not user.password_hash:
            raise AuthenticationError(
                "This account was registered using Google Sign-In. Please sign in with Google."
            )

        if not verify_password(request.password, user.password_hash):
            raise AuthenticationError("Invalid email or password.")

        # Seamlessly upgrade password hash if Argon2id parameters were tuned
        if needs_rehash(user.password_hash):
            new_hash = hash_password(request.password)
            self.user_repo.update_password_hash(user.id, new_hash)

        self.user_repo.update_last_login(user.id)

        # Issue session token and CSRF token
        raw_session_token = generate_opaque_token(32)
        session_hash = hash_token(raw_session_token)
        csrf_token = generate_csrf_token()

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=self.settings.session_cookie_ttl_days)

        self.session_repo.create_session(
            user_id=user.id,
            token_hash=session_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return user, raw_session_token, csrf_token

    def verify_email(self, raw_token: str) -> UserModel:
        """Redeem email verification token and update account status."""
        token_hash = hash_token(raw_token.strip())
        token = self.email_token_repo.get_valid_token(token_hash, "VERIFY_EMAIL")
        if not token:
            raise ValidationError("Invalid or expired verification token.")

        self.user_repo.mark_email_verified(token.user_id)
        self.email_token_repo.mark_token_used(token.id)

        user = self.user_repo.get_by_id(token.user_id)
        if not user:
            raise NotFoundError("User", token.user_id)
        return user

    def logout(self, raw_session_token: str) -> bool:
        """Revoke active session token."""
        if not raw_session_token:
            return False
        token_hash = hash_token(raw_session_token.strip())
        return self.session_repo.revoke_by_token_hash(token_hash)

    def validate_session(self, raw_session_token: str) -> Optional[UserModel]:
        """Validate session token, enforce sliding expiration touch, and return active user."""
        if not raw_session_token:
            return None
        token_hash = hash_token(raw_session_token.strip())
        session = self.session_repo.get_active_session_by_token_hash(token_hash)
        if not session or not session.user or not session.user.is_active:
            return None

        # Slide session activity window
        self.session_repo.touch_session(session.id)
        return session.user

    def request_password_reset(self, email: str) -> Optional[str]:
        """Generate a single-use password recovery token (anti-enumeration safe)."""
        try:
            norm_email = normalize_email(email)
        except ValueError:
            return None

        user = self.user_repo.get_by_email_normalized(norm_email)
        if not user or not user.is_active:
            return None

        raw_token = generate_opaque_token(32)
        token_hash = hash_token(raw_token)
        now = datetime.now(timezone.utc)
        self.email_token_repo.create_token(
            user_id=user.id,
            token_hash=token_hash,
            token_type="PASSWORD_RESET",
            expires_at=now + timedelta(hours=1),
        )
        return raw_token

    def reset_password(self, raw_token: str, new_password: str) -> bool:
        """Reset account password and revoke all existing active sessions."""
        token_hash = hash_token(raw_token.strip())
        token = self.email_token_repo.get_valid_token(token_hash, "PASSWORD_RESET")
        if not token:
            raise ValidationError("Invalid or expired password reset token.")

        new_hash = hash_password(new_password)
        self.user_repo.update_password_hash(token.user_id, new_hash)
        self.email_token_repo.mark_token_used(token.id)

        # Invalidate all active sessions across devices upon password reset
        self.session_repo.revoke_all_sessions_for_user(token.user_id)
        return True

    def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
        current_session_token: Optional[str] = None,
    ) -> bool:
        """Change password for authenticated user, preserving current session while rotating others."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)

        if not user.password_hash or not verify_password(current_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect.")

        new_hash = hash_password(new_password)
        self.user_repo.update_password_hash(user_id, new_hash)

        # Rotate sessions
        current_session_id = None
        if current_session_token:
            sess = self.session_repo.get_active_session_by_token_hash(hash_token(current_session_token.strip()))
            if sess:
                current_session_id = sess.id

        self.session_repo.revoke_all_sessions_for_user(user_id, except_session_id=current_session_id)
        return True

    def list_sessions(
        self,
        user_id: str,
        current_session_token: Optional[str] = None,
    ) -> list[SessionResponse]:
        """List active unrevoked sessions for an authenticated user."""
        current_token_hash = hash_token(current_session_token.strip()) if current_session_token else None
        sessions = self.session_repo.list_active_sessions_for_user(user_id)
        return [
            SessionResponse(
                id=s.id,
                created_at=s.created_at,
                expires_at=s.expires_at,
                last_used_at=s.last_used_at,
                ip_address=s.ip_address,
                user_agent=s.user_agent,
                is_current=(s.token_hash == current_token_hash),
            )
            for s in sessions
        ]

    def revoke_session(self, user_id: str, session_id: str) -> bool:
        """Revoke a specific session owned by the authenticated user."""
        session = self.session_repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            raise NotFoundError("Session", session_id)
        return self.session_repo.revoke_session(session_id)

    def to_user_response(self, user: UserModel) -> UserResponse:
        """Transform a UserModel into a UserResponse DTO."""
        identities = self.user_repo.get_identities_for_user(user.id)
        return UserResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            email_verified=bool(user.email_verified_at),
            is_active=user.is_active,
            has_password=bool(user.password_hash),
            identities=[
                UserIdentityResponse(
                    id=ident.id,
                    provider=ident.provider,
                    provider_email=ident.provider_email,
                    created_at=ident.created_at,
                )
                for ident in identities
            ],
            created_at=user.created_at,
        )
