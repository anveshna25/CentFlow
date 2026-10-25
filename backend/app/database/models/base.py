import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, func
from sqlalchemy.types import DateTime, TypeDecorator
from app.database.session import Base


class UTCDateTime(TypeDecorator):
    """DateTime type that guarantees timezone-aware UTC datetime objects across SQLite and PostgreSQL."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return value


def generate_uuid() -> str:
    """Generate string UUID v4 for primary keys."""
    return str(uuid.uuid4())


class TimestampMixin:
    """Audit timestamps mixin for stateful entities."""

    created_at = Column(
        UTCDateTime,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        UTCDateTime,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
