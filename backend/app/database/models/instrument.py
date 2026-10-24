from sqlalchemy import Boolean, Column, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.models.base import Base, TimestampMixin, generate_uuid


class InstrumentModel(Base, TimestampMixin):
    """SQLAlchemy model for instruments table."""

    __tablename__ = "instruments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    asset_id = Column(String(36), ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True)
    exchange_id = Column(String(36), ForeignKey("exchanges.id", ondelete="RESTRICT"), nullable=True, index=True)
    market_id = Column(String(36), ForeignKey("markets.id", ondelete="SET NULL"), nullable=True, index=True)

    symbol = Column(String(50), nullable=False, index=True)
    ticker = Column(String(50), nullable=True)
    name = Column(String(255), nullable=False)
    currency = Column(String(3), nullable=False)
    lot_size = Column(Numeric(18, 4), nullable=False, default=1.0)
    is_active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("exchange_id", "symbol", name="uq_instruments_exchange_symbol"),
    )

    asset = relationship("AssetModel", back_populates="instruments")
    exchange = relationship("ExchangeModel", back_populates="instruments")
    market = relationship("MarketModel", back_populates="instruments")
    prices = relationship("PriceModel", back_populates="instrument", cascade="all, delete-orphan")
    watchlist_associations = relationship("WatchlistInstrumentModel", back_populates="instrument", cascade="all, delete-orphan")
    positions = relationship("PositionModel", back_populates="instrument")
