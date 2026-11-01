from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.database.models.base import Base, TimestampMixin, generate_uuid


class UserModel(Base, TimestampMixin):
    """SQLAlchemy model for application users."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    email_normalized = Column(String(255), unique=True, index=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=True)  # Nullable for Google-only authentication
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    identities = relationship("UserIdentityModel", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSessionModel", back_populates="user", cascade="all, delete-orphan")
    email_tokens = relationship("EmailTokenModel", back_populates="user", cascade="all, delete-orphan")
    portfolios = relationship("PortfolioModel", back_populates="user", cascade="all, delete-orphan")
    watchlists = relationship("WatchlistModel", back_populates="user", cascade="all, delete-orphan")


class UserIdentityModel(Base):
    """SQLAlchemy model for external or local identity providers linked to a user."""

    __tablename__ = "user_identities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False)  # 'local', 'google'
    provider_subject = Column(String(255), nullable=False)
    provider_email = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("provider", "provider_subject", name="uq_identity_provider_subject"),
    )

    user = relationship("UserModel", back_populates="identities")


class UserSessionModel(Base):
    """SQLAlchemy model for opaque server-managed browser sessions."""

    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_used_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    revoked_at = Column(DateTime(timezone=True), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    user = relationship("UserModel", back_populates="sessions")


class EmailTokenModel(Base):
    """SQLAlchemy model for single-use email verification and password reset tokens."""

    __tablename__ = "email_tokens"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    token_type = Column(String(30), nullable=False)  # 'VERIFY_EMAIL', 'PASSWORD_RESET'
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("UserModel", back_populates="email_tokens")

