from typing import Optional
from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import enforce_csrf, get_current_user, get_optional_current_user
from app.api.schemas.auth import (
    AuthSuccessResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SessionResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.api.schemas.base import ResponseEnvelope
from app.core.config import get_settings
from app.database.models.user import UserModel
from app.database.session import get_db
from app.services.auth import AuthService
from app.services.google_auth import GoogleAuthService

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleCallbackRequest(BaseModel):
    """Payload for completing Google OAuth flow."""

    code: str
    state: str
    expected_state: str
    code_verifier: str


class GoogleAuthUrlResponse(BaseModel):
    """Response containing Google authorization URL and state parameters."""

    auth_url: str
    state: str
    code_verifier: str


class MessageResponse(BaseModel):
    """Generic status response payload."""

    message: str


def _set_auth_cookies(response: Response, session_token: str, csrf_token: str) -> None:
    """Helper to set HttpOnly session cookie and accessible CSRF cookie."""
    settings = get_settings()
    max_age = settings.session_cookie_ttl_days * 86400

    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_token,
        max_age=max_age,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        max_age=max_age,
        httponly=False,  # Accessible to JavaScript to attach to X-CSRF-Token header
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    """Helper to clear authentication cookies upon logout."""
    settings = get_settings()
    response.delete_cookie(key=settings.session_cookie_name, path="/")
    response.delete_cookie(key=settings.csrf_cookie_name, path="/")


@router.post("/register", response_model=ResponseEnvelope[AuthSuccessResponse], status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
) -> ResponseEnvelope[AuthSuccessResponse]:
    """Register a new user account with local credentials."""
    auth_service = AuthService(db)
    user, _ = auth_service.register(request)
    return ResponseEnvelope(
        data=AuthSuccessResponse(
            user=auth_service.to_user_response(user),
            message="Account registered successfully. Please verify your email.",
        )
    )


@router.post("/login", response_model=ResponseEnvelope[AuthSuccessResponse])
async def login(
    request_data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> ResponseEnvelope[AuthSuccessResponse]:
    """Authenticate with email and password, setting secure session cookies."""
    auth_service = AuthService(db)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    user, session_token, csrf_token = auth_service.login(
        request=request_data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    _set_auth_cookies(response, session_token, csrf_token)

    return ResponseEnvelope(
        data=AuthSuccessResponse(
            user=auth_service.to_user_response(user),
            message="Logged in successfully.",
        )
    )


@router.post("/logout", response_model=ResponseEnvelope[MessageResponse])
async def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> ResponseEnvelope[MessageResponse]:
    """Revoke active session and clear authentication cookies."""
    settings = get_settings()
    session_token = request.cookies.get(settings.session_cookie_name)
    if session_token:
        auth_service = AuthService(db)
        auth_service.logout(session_token)

    _clear_auth_cookies(response)
    return ResponseEnvelope(data=MessageResponse(message="Logged out successfully."))


@router.get("/me", response_model=ResponseEnvelope[UserResponse])
async def get_current_user_profile(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[UserResponse]:
    """Retrieve profile and linked identities of currently authenticated user."""
    auth_service = AuthService(db)
    return ResponseEnvelope(data=auth_service.to_user_response(current_user))


@router.get("/google/url", response_model=ResponseEnvelope[GoogleAuthUrlResponse])
async def get_google_auth_url(
    db: Session = Depends(get_db),
) -> ResponseEnvelope[GoogleAuthUrlResponse]:
    """Generate Google OAuth 2.0 authorization URL with PKCE parameters."""
    google_service = GoogleAuthService(db)
    data = google_service.generate_authorization_url()
    return ResponseEnvelope(
        data=GoogleAuthUrlResponse(
            auth_url=data["auth_url"],
            state=data["state"],
            code_verifier=data["code_verifier"],
        )
    )


@router.post("/google/callback", response_model=ResponseEnvelope[AuthSuccessResponse])
async def google_callback(
    payload: GoogleCallbackRequest,
    request: Request,
    response: Response,
    current_user: Optional[UserModel] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[AuthSuccessResponse]:
    """Exchange Google OAuth authorization code and create authenticated session or link identity."""
    google_service = GoogleAuthService(db)
    auth_service = AuthService(db)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    user, session_token, csrf_token = await google_service.handle_callback(
        code=payload.code,
        state=payload.state,
        expected_state=payload.expected_state,
        code_verifier=payload.code_verifier,
        ip_address=ip_address,
        user_agent=user_agent,
        authenticated_user_id=(current_user.id if current_user else None),
    )
    _set_auth_cookies(response, session_token, csrf_token)

    return ResponseEnvelope(
        data=AuthSuccessResponse(
            user=auth_service.to_user_response(user),
            message="Google authentication successful.",
        )
    )


@router.post("/verify-email", response_model=ResponseEnvelope[UserResponse])
async def verify_email(
    payload: VerifyEmailRequest,
    db: Session = Depends(get_db),
) -> ResponseEnvelope[UserResponse]:
    """Redeem email verification token."""
    auth_service = AuthService(db)
    user = auth_service.verify_email(payload.token)
    return ResponseEnvelope(data=auth_service.to_user_response(user))


@router.post("/forgot-password", response_model=ResponseEnvelope[MessageResponse])
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> ResponseEnvelope[MessageResponse]:
    """Request password reset link/token."""
    auth_service = AuthService(db)
    auth_service.request_password_reset(payload.email)
    return ResponseEnvelope(
        data=MessageResponse(
            message="If an account exists with this email, instructions have been sent."
        )
    )


@router.post("/reset-password", response_model=ResponseEnvelope[MessageResponse])
async def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> ResponseEnvelope[MessageResponse]:
    """Complete password reset using recovery token."""
    auth_service = AuthService(db)
    auth_service.reset_password(payload.token, payload.new_password)
    return ResponseEnvelope(data=MessageResponse(message="Password reset successfully. Please sign in."))


@router.post("/change-password", response_model=ResponseEnvelope[MessageResponse])
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    _csrf: None = Depends(enforce_csrf),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[MessageResponse]:
    """Change password for authenticated user and rotate other active sessions."""
    settings = get_settings()
    current_token = request.cookies.get(settings.session_cookie_name)
    auth_service = AuthService(db)
    auth_service.change_password(
        user_id=current_user.id,
        current_password=payload.current_password,
        new_password=payload.new_password,
        current_session_token=current_token,
    )
    return ResponseEnvelope(data=MessageResponse(message="Password changed successfully."))


@router.get("/sessions", response_model=ResponseEnvelope[list[SessionResponse]])
async def list_sessions(
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[list[SessionResponse]]:
    """List active unrevoked sessions for authenticated user."""
    settings = get_settings()
    current_token = request.cookies.get(settings.session_cookie_name)
    auth_service = AuthService(db)
    sessions = auth_service.list_sessions(current_user.id, current_token)
    return ResponseEnvelope(data=sessions)


@router.delete("/sessions/{session_id}", response_model=ResponseEnvelope[MessageResponse])
async def revoke_session(
    session_id: str,
    current_user: UserModel = Depends(get_current_user),
    _csrf: None = Depends(enforce_csrf),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[MessageResponse]:
    """Revoke a specific active session."""
    auth_service = AuthService(db)
    auth_service.revoke_session(current_user.id, session_id)
    return ResponseEnvelope(data=MessageResponse(message="Session revoked successfully."))

