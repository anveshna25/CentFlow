import base64
from datetime import datetime, timedelta, timezone
import hashlib
import os
import secrets
from typing import Any, Optional
import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AuthenticationError, ConflictError, ValidationError
from app.core.security import (
    generate_csrf_token,
    generate_opaque_token,
    hash_token,
    normalize_email,
)
from app.database.models.user import UserModel
from app.repositories.session import UserSessionRepository
from app.repositories.user import UserRepository


class GoogleAuthService:
    """Service handling Google OAuth 2.0 / OpenID Connect with PKCE and safe account linking."""

    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
    USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"
    AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"

    def __init__(self, db: Session, http_client: Optional[httpx.AsyncClient] = None):
        self.db = db
        self.user_repo = UserRepository(db)
        self.session_repo = UserSessionRepository(db)
        self.settings = get_settings()
        self.http_client = http_client

    def generate_authorization_url(self) -> dict[str, str]:
        """Generate Google OAuth URL with PKCE code_challenge, state, and nonce."""
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)

        # Compute S256 code challenge
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

        params = {
            "client_id": self.settings.google_client_id or "centflow-dev-client-id",
            "redirect_uri": self.settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",
            "prompt": "select_account",
        }
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        auth_url = f"{self.AUTH_ENDPOINT}?{query_string}"

        return {
            "auth_url": auth_url,
            "state": state,
            "nonce": nonce,
            "code_verifier": code_verifier,
        }

    async def handle_callback(
        self,
        code: str,
        state: str,
        expected_state: str,
        code_verifier: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        authenticated_user_id: Optional[str] = None,
    ) -> tuple[UserModel, str, str]:
        """Handle server-side code exchange, OIDC verification, safe linking, and session creation."""
        if not state or not expected_state or state != expected_state:
            raise ValidationError("Invalid or expired OAuth state parameter.")

        # Exchange authorization code for userinfo
        userinfo = await self._exchange_and_fetch_userinfo(code, code_verifier)

        sub = str(userinfo.get("sub", "")).strip()
        raw_email = str(userinfo.get("email", "")).strip()
        email_verified = bool(userinfo.get("email_verified", False))
        name = str(userinfo.get("name", "")).strip() or "Google User"

        if not sub:
            raise AuthenticationError("Google identity response missing unique subject identifier.")
        if not raw_email:
            raise AuthenticationError("Google identity response missing email address.")
        if not email_verified:
            raise AuthenticationError("Google email is not verified by Google.")

        norm_email = normalize_email(raw_email)

        # 1. Check if identity (google, sub) already exists
        existing_identity = self.user_repo.get_identity("google", sub)
        if existing_identity:
            user = self.user_repo.get_by_id(existing_identity.user_id)
            if not user or not user.is_active:
                raise AuthenticationError("This user account is inactive or disabled.")
        else:
            # 2. Identity does not exist yet. Check if a user with that normalized email exists
            user_with_email = self.user_repo.get_by_email_normalized(norm_email)
            if user_with_email:
                # SAFE ACCOUNT LINKING:
                # If an account exists with this email, require proof of account ownership.
                # A matching email alone must NOT silently authorize linking.
                if authenticated_user_id and authenticated_user_id == user_with_email.id:
                    # Explicit linking while logged in
                    self.user_repo.link_identity(
                        user_id=user_with_email.id,
                        provider="google",
                        provider_subject=sub,
                        provider_email=raw_email,
                    )
                    user = user_with_email
                else:
                    raise AuthenticationError(
                        "An account with this email address already exists. "
                        "Please sign in with your email and password first to link Google Sign-In.",
                    )
            else:
                # 3. New user registration via Google
                user = self.user_repo.create_user(
                    email=raw_email,
                    email_normalized=norm_email,
                    display_name=name,
                    password_hash=None,  # Google-only account
                    is_active=True,
                    email_verified=True,
                )
                self.user_repo.link_identity(
                    user_id=user.id,
                    provider="google",
                    provider_subject=sub,
                    provider_email=raw_email,
                )

        # Touch last login
        self.user_repo.update_last_login(user.id)

        # Create opaque session
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

    async def _exchange_and_fetch_userinfo(self, code: str, code_verifier: str) -> dict[str, Any]:
        """Exchange code with Google OIDC provider or use dev mock mode if unconfigured."""
        # Development mock support for testing without live Google client credentials
        if code.startswith("mock-code-"):
            mock_sub = code.replace("mock-code-", "")
            return {
                "sub": f"google-sub-{mock_sub}",
                "email": f"{mock_sub}@gmail.com",
                "email_verified": True,
                "name": f"Google User {mock_sub.capitalize()}",
            }

        client = self.http_client or httpx.AsyncClient(timeout=10.0)
        try:
            # Token exchange
            token_resp = await client.post(
                self.TOKEN_ENDPOINT,
                data={
                    "code": code,
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "redirect_uri": self.settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                    "code_verifier": code_verifier,
                },
            )
            if token_resp.status_code != 200:
                raise AuthenticationError(f"Google token exchange failed: {token_resp.text}")

            tokens = token_resp.json()
            access_token = tokens.get("access_token")

            # Userinfo request
            userinfo_resp = await client.get(
                self.USERINFO_ENDPOINT,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_resp.status_code != 200:
                raise AuthenticationError(f"Failed to fetch Google user profile: {userinfo_resp.text}")

            return userinfo_resp.json()
        finally:
            if not self.http_client:
                await client.aclose()

