from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from app.database.models.user import UserModel, UserSessionModel
from app.repositories.base import BaseRepository


class UserSessionRepository(BaseRepository[UserSessionModel]):
    """Repository handling persistence operations for user sessions."""

    def __init__(self, db: Session):
        super().__init__(UserSessionModel, db)

    def create_session(
        self,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> UserSessionModel:
        """Create and persist a new user session."""
        session = UserSessionModel(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_active_session_by_token_hash(self, token_hash: str) -> Optional[UserSessionModel]:
        """Lookup an unrevoked, unexpired session with eager-loaded User."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(UserSessionModel)
            .where(
                UserSessionModel.token_hash == token_hash,
                UserSessionModel.revoked_at.is_(None),
                UserSessionModel.expires_at > now,
            )
            .options(joinedload(UserSessionModel.user))
        )
        return self.db.scalars(stmt).first()

    def touch_session(self, session_id: str) -> None:
        """Update last_used_at timestamp on active session."""
        session = self.get_by_id(session_id)
        if session:
            session.last_used_at = datetime.now(timezone.utc)
            self.db.commit()

    def revoke_session(self, session_id: str) -> bool:
        """Mark a session as revoked."""
        session = self.get_by_id(session_id)
        if session and not session.revoked_at:
            session.revoked_at = datetime.now(timezone.utc)
            self.db.commit()
            return True
        return False

    def revoke_by_token_hash(self, token_hash: str) -> bool:
        """Revoke a session by its token hash."""
        stmt = select(UserSessionModel).where(
            UserSessionModel.token_hash == token_hash,
            UserSessionModel.revoked_at.is_(None),
        )
        session = self.db.scalars(stmt).first()
        if session:
            session.revoked_at = datetime.now(timezone.utc)
            self.db.commit()
            return True
        return False

    def revoke_all_sessions_for_user(self, user_id: str, except_session_id: Optional[str] = None) -> int:
        """Revoke all active sessions for a user (e.g. upon password reset or security rotation)."""
        now = datetime.now(timezone.utc)
        stmt = select(UserSessionModel).where(
            UserSessionModel.user_id == user_id,
            UserSessionModel.revoked_at.is_(None),
        )
        if except_session_id:
            stmt = stmt.where(UserSessionModel.id != except_session_id)
        sessions = self.db.scalars(stmt).all()
        count = 0
        for s in sessions:
            s.revoked_at = now
            count += 1
        if count > 0:
            self.db.commit()
        return count

    def list_active_sessions_for_user(self, user_id: str) -> list[UserSessionModel]:
        """Fetch all currently active unexpired sessions for a user."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(UserSessionModel)
            .where(
                UserSessionModel.user_id == user_id,
                UserSessionModel.revoked_at.is_(None),
                UserSessionModel.expires_at > now,
            )
            .order_by(UserSessionModel.last_used_at.desc())
        )
        return list(self.db.scalars(stmt).all())
