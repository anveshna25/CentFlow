from sqlalchemy import Boolean, Column, String
from sqlalchemy.orm import relationship
from app.database.models.base import Base, TimestampMixin, generate_uuid


class ExchangeModel(Base, TimestampMixin):
    """SQLAlchemy model for exchanges table."""

    __tablename__ = "exchanges"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(20), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    mic = Column(String(10), nullable=True, unique=True, index=True)
    country = Column(String(100), nullable=True)
    country_code = Column(String(2), nullable=True)
    timezone = Column(String(50), nullable=True)
    currency = Column(String(3), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    instruments = relationship("InstrumentModel", back_populates="exchange")

    def to_domain(self):
        from app.domain.models import Exchange

        return Exchange(
            id=self.id,
            name=self.name,
            code=self.code,
            country=self.country,
            country_code=self.country_code,
            timezone=self.timezone,
            currency=self.currency,
            is_active=self.is_active,
        )
