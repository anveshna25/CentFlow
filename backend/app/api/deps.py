from typing import Optional
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AuthenticationError, ValidationError
from app.core.security import validate_csrf_token
from app.database.models.user import UserModel
from app.database.session import get_db
from app.services.auth import AuthService


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> UserModel:
    """FastAPI dependency to extract and validate the authenticated user from the session cookie."""
    settings = get_settings()
    session_token = request.cookies.get(settings.session_cookie_name)
    if not session_token:
        raise AuthenticationError("Authentication required. Please sign in.")

    auth_service = AuthService(db)
    user = auth_service.validate_session(session_token)
    if not user:
        raise AuthenticationError("Your session has expired or was revoked. Please sign in again.")

    return user


def get_optional_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[UserModel]:
    """FastAPI dependency that returns the authenticated user if session cookie exists, or None."""
    settings = get_settings()
    session_token = request.cookies.get(settings.session_cookie_name)
    if not session_token:
        return None

    auth_service = AuthService(db)
    return auth_service.validate_session(session_token)


def enforce_csrf(request: Request) -> None:
    """Enforce double-submit CSRF token validation on state-mutating requests (POST, PUT, DELETE, PATCH)."""
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        settings = get_settings()
        cookie_csrf = request.cookies.get(settings.csrf_cookie_name)
        header_csrf = request.headers.get("X-CSRF-Token")

        # Only enforce CSRF if session cookie is present (authenticated browser requests)
        session_cookie = request.cookies.get(settings.session_cookie_name)
        if session_cookie:
            if not validate_csrf_token(cookie_csrf, header_csrf):
                raise ValidationError("CSRF verification failed. Missing or invalid X-CSRF-Token header.")

