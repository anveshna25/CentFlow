from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.models.base import Base, TimestampMixin, generate_uuid


class PortfolioModel(Base, TimestampMixin):
    """SQLAlchemy model for portfolios table."""

    __tablename__ = "portfolios"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    base_currency = Column(String(3), nullable=False, default="USD")
    user_id = Column(String(36), nullable=True, index=True)

    positions = relationship("PositionModel", back_populates="portfolio", cascade="all, delete-orphan")


class PositionModel(Base, TimestampMixin):
    """SQLAlchemy model for positions table."""

    __tablename__ = "positions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    portfolio_id = Column(String(36), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    instrument_id = Column(String(36), ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False, index=True)

    quantity = Column(Numeric(18, 8), nullable=False)
    average_price = Column(Numeric(18, 6), nullable=False)
    currency = Column(String(3), nullable=False)
    opened_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("portfolio_id", "instrument_id", name="uq_portfolio_instrument"),
    )

    portfolio = relationship("PortfolioModel", back_populates="positions")
    instrument = relationship("InstrumentModel", back_populates="positions")
