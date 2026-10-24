from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.database.models.base import Base, generate_uuid


class PriceModel(Base):
    """SQLAlchemy model for prices (market data observations) table."""

    __tablename__ = "prices"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    instrument_id = Column(String(36), ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False, index=True)

    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    price = Column(Numeric(18, 6), nullable=False)
    open = Column(Numeric(18, 6), nullable=True)
    high = Column(Numeric(18, 6), nullable=True)
    low = Column(Numeric(18, 6), nullable=True)
    close = Column(Numeric(18, 6), nullable=True)
    volume = Column(Numeric(24, 4), nullable=True)
    currency = Column(String(3), nullable=False)
    interval = Column(String(20), nullable=False, default="tick")
    source = Column(String(50), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_prices_instrument_timestamp", "instrument_id", "timestamp"),
        Index("idx_prices_interval_lookup", "instrument_id", "interval", "timestamp"),
        UniqueConstraint("instrument_id", "interval", "timestamp", "source", name="uq_prices_dedup"),
    )

    instrument = relationship("InstrumentModel", back_populates="prices")
