from collections.abc import Sequence
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from app.database.models.watchlist import WatchlistInstrumentModel, WatchlistModel
from app.repositories.base import BaseRepository


class WatchlistRepository(BaseRepository[WatchlistModel]):
    """Repository handling persistence operations for watchlists and item associations."""

    def __init__(self, db: Session):
        super().__init__(WatchlistModel, db)

    def list_watchlists(self, user_id: Optional[str] = None) -> Sequence[WatchlistModel]:
        """Retrieve all watchlists, optionally filtered by user_id."""
        stmt = (
            select(WatchlistModel)
            .options(
                joinedload(WatchlistModel.items).joinedload(WatchlistInstrumentModel.instrument)
            )
            .order_by(WatchlistModel.created_at.asc())
        )
        if user_id:
            stmt = stmt.where(WatchlistModel.user_id == user_id)
        return self.db.scalars(stmt).unique().all()

    def get_by_id_with_items(self, watchlist_id: str) -> Optional[WatchlistModel]:
        """Retrieve a watchlist along with its associated instruments."""
        stmt = (
            select(WatchlistModel)
            .options(
                joinedload(WatchlistModel.items).joinedload(WatchlistInstrumentModel.instrument)
            )
            .where(WatchlistModel.id == watchlist_id)
        )
        return self.db.scalars(stmt).unique().first()

    def get_or_create_default(
        self,
        name: str = "My Watchlist",
        description: str = "Default asset watchlist",
        user_id: Optional[str] = None,
    ) -> WatchlistModel:
        """Fetch the first active watchlist or create a default one if none exist."""
        stmt = select(WatchlistModel).order_by(WatchlistModel.created_at.asc())
        if user_id:
            stmt = stmt.where(WatchlistModel.user_id == user_id)
        existing = self.db.scalars(stmt).first()
        if existing:
            return existing

        default_wl = WatchlistModel(
            name=name,
            description=description,
            user_id=user_id,
        )
        return self.create(default_wl)

    def add_instrument(
        self,
        watchlist_id: str,
        instrument_id: str,
    ) -> tuple[WatchlistInstrumentModel, bool]:
        """Add an instrument to a watchlist with duplicate prevention.

        Returns:
            tuple[WatchlistInstrumentModel, bool]: (item, was_created)
        """
        # Check for existing association (duplicate check)
        stmt = select(WatchlistInstrumentModel).where(
            WatchlistInstrumentModel.watchlist_id == watchlist_id,
            WatchlistInstrumentModel.instrument_id == instrument_id,
        )
        existing = self.db.scalars(stmt).first()
        if existing:
            return existing, False

        # Determine next display order
        order_stmt = select(func.count(WatchlistInstrumentModel.id)).where(
            WatchlistInstrumentModel.watchlist_id == watchlist_id
        )
        current_count = self.db.scalar(order_stmt) or 0

        item = WatchlistInstrumentModel(
            watchlist_id=watchlist_id,
            instrument_id=instrument_id,
            display_order=current_count + 1,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item, True

    def remove_instrument(self, watchlist_id: str, instrument_id: str) -> bool:
        """Remove an instrument from a watchlist. Returns True if removed, False if not found."""
        stmt = select(WatchlistInstrumentModel).where(
            WatchlistInstrumentModel.watchlist_id == watchlist_id,
            WatchlistInstrumentModel.instrument_id == instrument_id,
        )
        item = self.db.scalars(stmt).first()
        if not item:
            return False

        self.db.delete(item)
        self.db.commit()
        return True

    def get_items(self, watchlist_id: str) -> Sequence[WatchlistInstrumentModel]:
        """Retrieve ordered items for a watchlist."""
        stmt = (
            select(WatchlistInstrumentModel)
            .options(joinedload(WatchlistInstrumentModel.instrument))
            .where(WatchlistInstrumentModel.watchlist_id == watchlist_id)
            .order_by(WatchlistInstrumentModel.display_order.asc(), WatchlistInstrumentModel.added_at.asc())
        )
        return self.db.scalars(stmt).all()
