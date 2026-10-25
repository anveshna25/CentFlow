from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.database.models.exchange import ExchangeModel
from app.repositories.base import BaseRepository


class ExchangeRepository(BaseRepository[ExchangeModel]):
    """Repository handling persistence operations for financial exchanges and venues."""

    def __init__(self, db: Session):
        super().__init__(ExchangeModel, db)

    def get_by_code(self, code: str) -> Optional[ExchangeModel]:
        """Lookup an exchange by its venue code (e.g., NASDAQ, NYSE, BINANCE)."""
        stmt = select(ExchangeModel).where(func.upper(ExchangeModel.code) == code.strip().upper())
        return self.db.scalars(stmt).first()

    def get_or_create(
        self,
        code: str,
        name: Optional[str] = None,
        country: Optional[str] = None,
        currency: Optional[str] = None,
    ) -> ExchangeModel:
        """Retrieve an existing exchange or persist a new one if not present."""
        clean_code = code.strip().upper()
        existing = self.get_by_code(clean_code)
        if existing:
            return existing

        exchange = ExchangeModel(
            code=clean_code,
            name=name.strip() if name else clean_code,
            country=country,
            currency=currency,
            is_active=True,
        )
        return self.create(exchange)
