from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.models.user import UserIdentityModel, UserModel
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[UserModel]):
    """Repository handling persistence operations for users and identities."""

    def __init__(self, db: Session):
        super().__init__(UserModel, db)

    def get_by_id(self, user_id: str) -> Optional[UserModel]:
        """Fetch user by primary key ID."""
        return self.db.get(self.model, user_id)

    def get_by_email_normalized(self, email_normalized: str) -> Optional[UserModel]:
        """Lookup a user by their unique normalized email."""
        stmt = select(UserModel).where(UserModel.email_normalized == email_normalized)
        return self.db.scalars(stmt).first()

    def create_user(
        self,
        email: str,
        email_normalized: str,
        display_name: str,
        password_hash: Optional[str] = None,
        is_active: bool = True,
        email_verified: bool = False,
    ) -> UserModel:
        """Create and persist a new user entity."""
        user = UserModel(
            email=email,
            email_normalized=email_normalized,
            display_name=display_name,
            password_hash=password_hash,
            is_active=is_active,
            email_verified_at=datetime.now(timezone.utc) if email_verified else None,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_password_hash(self, user_id: str, new_hash: str) -> None:
        """Update password hash and timestamp for a user."""
        user = self.get_by_id(user_id)
        if user:
            user.password_hash = new_hash
            user.updated_at = datetime.now(timezone.utc)
            self.db.commit()

    def mark_email_verified(self, user_id: str) -> None:
        """Set email_verified_at timestamp."""
        user = self.get_by_id(user_id)
        if user and not user.email_verified_at:
            user.email_verified_at = datetime.now(timezone.utc)
            self.db.commit()

    def update_last_login(self, user_id: str) -> None:
        """Update last_login_at timestamp."""
        user = self.get_by_id(user_id)
        if user:
            user.last_login_at = datetime.now(timezone.utc)
            self.db.commit()

    def link_identity(
        self,
        user_id: str,
        provider: str,
        provider_subject: str,
        provider_email: Optional[str] = None,
    ) -> UserIdentityModel:
        """Link an authentication provider identity to a user."""
        identity = UserIdentityModel(
            user_id=user_id,
            provider=provider,
            provider_subject=provider_subject,
            provider_email=provider_email,
        )
        self.db.add(identity)
        self.db.commit()
        self.db.refresh(identity)
        return identity

    def get_identity(self, provider: str, provider_subject: str) -> Optional[UserIdentityModel]:
        """Find a linked identity by provider and provider subject ID."""
        stmt = select(UserIdentityModel).where(
            UserIdentityModel.provider == provider,
            UserIdentityModel.provider_subject == provider_subject,
        )
        return self.db.scalars(stmt).first()

    def get_identities_for_user(self, user_id: str) -> list[UserIdentityModel]:
        """Fetch all linked identities for a specific user."""
        stmt = select(UserIdentityModel).where(UserIdentityModel.user_id == user_id)
        return list(self.db.scalars(stmt).all())
