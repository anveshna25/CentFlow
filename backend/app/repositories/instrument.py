from collections.abc import Sequence
from typing import Optional
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload
from app.database.models.instrument import InstrumentModel
from app.providers.base import ProviderInstrument
from app.repositories.asset import AssetRepository
from app.repositories.base import BaseRepository
from app.repositories.exchange import ExchangeRepository


class InstrumentRepository(BaseRepository[InstrumentModel]):
    """Repository handling persistence operations for tradable instruments."""

    def __init__(self, db: Session):
        super().__init__(InstrumentModel, db)
        self.asset_repo = AssetRepository(db)
        self.exchange_repo = ExchangeRepository(db)

    def get_by_symbol(self, symbol: str) -> Optional[InstrumentModel]:
        """Lookup an instrument by ticker symbol."""
        stmt = select(InstrumentModel).where(func.upper(InstrumentModel.symbol) == symbol.strip().upper())
        return self.db.scalars(stmt).first()

    def get_with_relations(self, symbol_or_id: str) -> Optional[InstrumentModel]:
        """Lookup an instrument by ID or symbol with asset, exchange, and market loaded."""
        stmt = (
            select(InstrumentModel)
            .options(
                joinedload(InstrumentModel.asset),
                joinedload(InstrumentModel.exchange),
                joinedload(InstrumentModel.market),
            )
            .where(
                (InstrumentModel.id == symbol_or_id)
                | (func.upper(InstrumentModel.symbol) == symbol_or_id.strip().upper())
                | (func.upper(InstrumentModel.ticker) == symbol_or_id.strip().upper())
            )
        )
        return self.db.scalars(stmt).first()

    def get_by_provider_symbol(self, provider_symbol: str) -> Optional[InstrumentModel]:
        """Lookup an instrument by provider symbol/ticker, falling back to symbol."""
        clean = provider_symbol.strip().upper()
        stmt = (
            select(InstrumentModel)
            .options(
                joinedload(InstrumentModel.asset),
                joinedload(InstrumentModel.exchange),
                joinedload(InstrumentModel.market),
            )
            .where(
                (func.upper(InstrumentModel.ticker) == clean)
                | (func.upper(InstrumentModel.symbol) == clean)
            )
        )
        return self.db.scalars(stmt).first()

    def list_by_asset(self, asset_id: str, active_only: bool = True) -> Sequence[InstrumentModel]:
        """List instruments belonging to a specific asset."""
        stmt = (
            select(InstrumentModel)
            .options(
                joinedload(InstrumentModel.exchange),
                joinedload(InstrumentModel.market),
            )
            .where(InstrumentModel.asset_id == asset_id)
        )
        if active_only:
            stmt = stmt.where(InstrumentModel.is_active == True)  # noqa: E712
        stmt = stmt.order_by(InstrumentModel.symbol.asc())
        return self.db.scalars(stmt).all()

    def list_with_relations(
        self,
        asset_id: Optional[str] = None,
        exchange_code: Optional[str] = None,
        active_only: bool = True,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[InstrumentModel]:
        """List instruments with joined asset, exchange, and market relations."""
        stmt = (
            select(InstrumentModel)
            .options(
                joinedload(InstrumentModel.asset),
                joinedload(InstrumentModel.exchange),
                joinedload(InstrumentModel.market),
            )
        )
        if asset_id:
            stmt = stmt.where(InstrumentModel.asset_id == asset_id)
        if active_only:
            stmt = stmt.where(InstrumentModel.is_active == True)  # noqa: E712
        if exchange_code:
            from app.database.models.exchange import ExchangeModel
            stmt = stmt.join(InstrumentModel.exchange).where(
                func.upper(ExchangeModel.code) == exchange_code.strip().upper()
            )
        stmt = stmt.order_by(InstrumentModel.symbol.asc()).offset(offset).limit(limit)
        return self.db.scalars(stmt).all()

    def search(self, query: str, limit: int = 50) -> Sequence[InstrumentModel]:
        """Search instruments by matching symbol or name keywords."""
        clean_q = f"%{query.strip().lower()}%"
        stmt = (
            select(InstrumentModel)
            .where(
                or_(
                    func.lower(InstrumentModel.symbol).like(clean_q),
                    func.lower(InstrumentModel.name).like(clean_q),
                )
            )
            .limit(limit)
        )
        return self.db.scalars(stmt).all()

    def list_active(self, offset: int = 0, limit: int = 100) -> Sequence[InstrumentModel]:
        """Retrieve paginated active instruments."""
        stmt = (
            select(InstrumentModel)
            .where(InstrumentModel.is_active == True)  # noqa: E712
            .offset(offset)
            .limit(limit)
        )
        return self.db.scalars(stmt).all()

    def count_instruments(self, active_only: bool = False) -> int:
        """Count total instruments in the database, optionally filtering by active state."""
        stmt = select(func.count(InstrumentModel.id))
        if active_only:
            stmt = stmt.where(InstrumentModel.is_active == True)  # noqa: E712
        return self.db.scalar(stmt) or 0

    def get_or_create_from_provider(
        self,
        provider_inst: ProviderInstrument,
        default_currency: str = "USD",
    ) -> InstrumentModel:
        """Upsert and associate instrument with its corresponding asset and exchange."""
        clean_symbol = provider_inst.symbol.strip().upper()
        existing = self.get_by_symbol(clean_symbol)
        if existing:
            # Sync any enriched metadata
            updated = False
            if provider_inst.name and existing.name != provider_inst.name:
                existing.name = provider_inst.name
                updated = True
            if provider_inst.currency and existing.currency != provider_inst.currency.upper():
                existing.currency = provider_inst.currency.upper()
                updated = True
            if updated:
                self.update(existing)
            return existing

        asset_name = provider_inst.name or clean_symbol
        asset_class = (provider_inst.asset_type or "equity").lower()
        asset = self.asset_repo.get_or_create(name=asset_name, asset_class=asset_class)

        exchange = None
        if provider_inst.exchange:
            exchange = self.exchange_repo.get_or_create(code=provider_inst.exchange)

        currency = (provider_inst.currency or default_currency).strip().upper()
        instrument = InstrumentModel(
            asset_id=asset.id,
            exchange_id=exchange.id if exchange else None,
            symbol=clean_symbol,
            ticker=clean_symbol,
            name=provider_inst.name or clean_symbol,
            currency=currency,
            lot_size=1.0,
            is_active=True,
        )
        return self.create(instrument)
