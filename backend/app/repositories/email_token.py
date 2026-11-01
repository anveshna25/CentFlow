from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.models.user import EmailTokenModel
from app.repositories.base import BaseRepository


class EmailTokenRepository(BaseRepository[EmailTokenModel]):
    """Repository handling single-use verification and password-reset tokens."""

    def __init__(self, db: Session):
        super().__init__(EmailTokenModel, db)

    def create_token(
        self,
        user_id: str,
        token_hash: str,
        token_type: str,
        expires_at: datetime,
    ) -> EmailTokenModel:
        """Create and persist a single-use token."""
        token = EmailTokenModel(
            user_id=user_id,
            token_hash=token_hash,
            token_type=token_type,
            expires_at=expires_at,
        )
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def get_valid_token(self, token_hash: str, token_type: str) -> Optional[EmailTokenModel]:
        """Lookup an unexpired, unused token by hash and type."""
        now = datetime.now(timezone.utc)
        stmt = select(EmailTokenModel).where(
            EmailTokenModel.token_hash == token_hash,
            EmailTokenModel.token_type == token_type,
            EmailTokenModel.used_at.is_(None),
            EmailTokenModel.expires_at > now,
        )
        return self.db.scalars(stmt).first()

    def mark_token_used(self, token_id: str) -> None:
        """Mark single-use token as redeemed."""
        token = self.get_by_id(token_id)
        if token and not token.used_at:
            token.used_at = datetime.now(timezone.utc)
            self.db.commit()
