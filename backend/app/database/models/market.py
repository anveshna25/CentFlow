from sqlalchemy import Boolean, Column, String, Text
from sqlalchemy.orm import relationship
from app.database.models.base import Base, TimestampMixin, generate_uuid


class MarketModel(Base, TimestampMixin):
    """SQLAlchemy model for markets table."""

    __tablename__ = "markets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    region = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    instruments = relationship("InstrumentModel", back_populates="market")
