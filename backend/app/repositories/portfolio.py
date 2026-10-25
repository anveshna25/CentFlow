from collections.abc import Sequence
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from app.database.models.portfolio import PortfolioModel, PositionModel
from app.repositories.base import BaseRepository


class PortfolioRepository(BaseRepository[PortfolioModel]):
    """Repository handling persistence operations for investment portfolios and positions."""

    def __init__(self, db: Session):
        super().__init__(PortfolioModel, db)

    def list_with_positions(self, user_id: Optional[str] = None) -> Sequence[PortfolioModel]:
        """Retrieve portfolios with eager-loaded positions and associated instruments."""
        stmt = (
            select(PortfolioModel)
            .options(
                joinedload(PortfolioModel.positions).joinedload(PositionModel.instrument)
            )
            .order_by(PortfolioModel.created_at.desc())
        )
        if user_id:
            stmt = stmt.where(PortfolioModel.user_id == user_id)
        return self.db.scalars(stmt).unique().all()

    def get_with_positions(self, portfolio_id: str) -> Optional[PortfolioModel]:
        """Fetch a single portfolio with eager-loaded positions and instrument relations."""
        stmt = (
            select(PortfolioModel)
            .where(PortfolioModel.id == portfolio_id)
            .options(
                joinedload(PortfolioModel.positions).joinedload(PositionModel.instrument)
            )
        )
        return self.db.scalars(stmt).unique().first()

    def add_or_update_position(
        self,
        portfolio_id: str,
        instrument_id: str,
        quantity: Decimal,
        average_price: Decimal,
        currency: str = "USD",
        opened_at: Optional[datetime] = None,
    ) -> PositionModel:
        """Add a new position or update an existing position within a portfolio."""
        stmt = select(PositionModel).where(
            PositionModel.portfolio_id == portfolio_id,
            PositionModel.instrument_id == instrument_id,
        )
        pos = self.db.scalars(stmt).first()
        if pos:
            # Calculate weighted average entry price
            total_qty = pos.quantity + quantity
            if total_qty > 0:
                total_cost = (pos.quantity * pos.average_price) + (quantity * average_price)
                pos.average_price = total_cost / total_qty
                pos.quantity = total_qty
            else:
                pos.quantity = Decimal("0")
            pos.currency = currency
        else:
            pos = PositionModel(
                portfolio_id=portfolio_id,
                instrument_id=instrument_id,
                quantity=quantity,
                average_price=average_price,
                currency=currency,
                opened_at=opened_at or datetime.now(timezone.utc),
            )
            self.db.add(pos)

        self.db.commit()
        self.db.refresh(pos)
        return pos

    def get_position(self, portfolio_id: str, position_id: str) -> Optional[PositionModel]:
        """Lookup a specific position within a portfolio."""
        stmt = (
            select(PositionModel)
            .where(
                PositionModel.portfolio_id == portfolio_id,
                PositionModel.id == position_id,
            )
            .options(joinedload(PositionModel.instrument))
        )
        return self.db.scalars(stmt).first()

    def delete_position(self, portfolio_id: str, position_id: str) -> bool:
        """Remove a position from a portfolio."""
        pos = self.get_position(portfolio_id, position_id)
        if not pos:
            return False
        self.db.delete(pos)
        self.db.commit()
        return True
