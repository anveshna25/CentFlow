from sqlalchemy import Boolean, Column, String, Text
from sqlalchemy.orm import relationship
from app.database.models.base import Base, TimestampMixin, generate_uuid


class AssetModel(Base, TimestampMixin):
    """SQLAlchemy model for assets table."""

    __tablename__ = "assets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    asset_class = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    instruments = relationship("InstrumentModel", back_populates="asset")
