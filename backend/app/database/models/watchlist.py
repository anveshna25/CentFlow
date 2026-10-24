from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.database.models.base import Base, TimestampMixin, generate_uuid


class WatchlistModel(Base, TimestampMixin):
    """SQLAlchemy model for watchlists table."""

    __tablename__ = "watchlists"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    user_id = Column(String(36), nullable=True, index=True)

    items = relationship(
        "WatchlistInstrumentModel",
        back_populates="watchlist",
        cascade="all, delete-orphan",
        order_by="WatchlistInstrumentModel.display_order",
    )


class WatchlistInstrumentModel(Base):
    """SQLAlchemy associative join model for watchlist_instruments table."""

    __tablename__ = "watchlist_instruments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    watchlist_id = Column(String(36), ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False, index=True)
    instrument_id = Column(String(36), ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False, index=True)
    display_order = Column(Integer, nullable=False, default=0)

    added_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("watchlist_id", "instrument_id", name="uq_watchlist_instrument"),
    )

    watchlist = relationship("WatchlistModel", back_populates="items")
    instrument = relationship("InstrumentModel", back_populates="watchlist_associations")
