import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String, func
from app.database.session import Base


def generate_uuid() -> str:
    """Generate string UUID v4 for primary keys."""
    return str(uuid.uuid4())


class TimestampMixin:
    """Audit timestamps mixin for stateful entities."""

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
