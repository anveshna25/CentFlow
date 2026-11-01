import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.database.models.watchlist import WatchlistModel
from app.providers.base import ProviderInstrument
from app.repositories.instrument import InstrumentRepository
from app.repositories.watchlist import WatchlistRepository
from app.services.market_data import MarketDataService

logger = logging.getLogger(__name__)

DEFAULT_LEGACY_USER_ID = "legacy-dev-user-0000-000000000001"


@dataclass
class WatchlistItemDTO:
    """Enriched data transfer representation of an instrument within a watchlist."""

    id: str
    instrument_id: str
    symbol: str
    name: str
    currency: str
    exchange: Optional[str]
    asset_type: Optional[str]
    added_at: datetime
    price: Optional[Decimal] = None
    change: Optional[Decimal] = None
    change_pct: Optional[Decimal] = None
    is_up: Optional[bool] = None


@dataclass
class WatchlistDTO:
    """Enriched watchlist response containing tracked instrument items."""

    id: str
    name: str
    description: Optional[str]
    items_count: int
    items: list[WatchlistItemDTO]
    created_at: Optional[datetime] = None


@dataclass
class WatchlistSummaryDTO:
    """Summary representation for watchlist catalog listings."""

    id: str
    name: str
    description: Optional[str]
    items_count: int
    symbols: list[str]
    created_at: Optional[datetime] = None


class WatchlistService:
    """Service layer orchestrating watchlist management, persistence, and quote enrichment."""

    def __init__(
        self,
        db: Session,
        market_data_service: Optional[MarketDataService] = None,
    ) -> None:
        self.db = db
        self.watchlist_repo = WatchlistRepository(db)
        self.instrument_repo = InstrumentRepository(db)
        self.market_data_service = market_data_service or MarketDataService()

    async def list_watchlists(self, user_id: Optional[str] = None) -> list[WatchlistSummaryDTO]:
        """List all watchlists scoped to user with summary symbols."""
        uid = user_id or DEFAULT_LEGACY_USER_ID
        watchlists = self.watchlist_repo.list_watchlists(user_id=uid)
        if not watchlists:
            default_wl = self.watchlist_repo.get_or_create_default(user_id=uid)
            watchlists = [default_wl]

        summaries: list[WatchlistSummaryDTO] = []
        for wl in watchlists:
            symbols = [
                item.instrument.symbol
                for item in wl.items
                if item.instrument and item.instrument.symbol
            ]
            summaries.append(
                WatchlistSummaryDTO(
                    id=wl.id,
                    name=wl.name,
                    description=wl.description,
                    items_count=len(wl.items),
                    symbols=symbols,
                    created_at=wl.created_at,
                )
            )
        return summaries

    async def get_watchlist(
        self,
        watchlist_id: str,
        user_id: Optional[str] = None,
        enrich_quotes: bool = True,
    ) -> Optional[WatchlistDTO]:
        """Retrieve a specific user-owned watchlist, enriching items with live market quotes."""
        wl = self.watchlist_repo.get_by_id_with_items(watchlist_id, user_id=user_id)
        if not wl:
            return None

        enriched_items: list[WatchlistItemDTO] = []
        for item in wl.items:
            inst = item.instrument
            if not inst:
                continue

            dto = WatchlistItemDTO(
                id=item.id,
                instrument_id=inst.id,
                symbol=inst.symbol,
                name=inst.name,
                currency=inst.currency,
                exchange=inst.exchange.code if inst.exchange else None,
                asset_type=inst.asset.asset_class if inst.asset else None,
                added_at=item.added_at,
            )

            if enrich_quotes:
                try:
                    quote = await self.market_data_service.get_quote(inst.symbol)
                    dto.price = quote.price
                    dto.change = quote.change
                    dto.change_pct = quote.change_percent
                    dto.is_up = quote.change >= 0 if quote.change is not None else True
                except Exception as ex:
                    logger.warning(
                        "Unable to fetch live quote for watchlist symbol %s: %s",
                        inst.symbol,
                        ex,
                    )

            enriched_items.append(dto)

        return WatchlistDTO(
            id=wl.id,
            name=wl.name,
            description=wl.description,
            items_count=len(enriched_items),
            items=enriched_items,
            created_at=wl.created_at,
        )

    async def get_or_create_default(
        self,
        user_id: Optional[str] = None,
        enrich_quotes: bool = True,
    ) -> WatchlistDTO:
        """Fetch or create the default watchlist for user and return enriched details."""
        uid = user_id or DEFAULT_LEGACY_USER_ID
        default_wl = self.watchlist_repo.get_or_create_default(user_id=uid)
        res = await self.get_watchlist(default_wl.id, user_id=uid, enrich_quotes=enrich_quotes)
        if res is not None:
            return res
        return WatchlistDTO(
            id=default_wl.id,
            name=default_wl.name,
            description=default_wl.description,
            items_count=0,
            items=[],
            created_at=default_wl.created_at,
        )

    async def create_watchlist(
        self,
        name: str,
        user_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> WatchlistDTO:
        """Create a new user-owned watchlist."""
        uid = user_id or DEFAULT_LEGACY_USER_ID
        clean_name = name.strip()
        wl = WatchlistModel(
            name=clean_name,
            description=description.strip() if description else None,
            user_id=uid,
        )
        created = self.watchlist_repo.create(wl)
        return WatchlistDTO(
            id=created.id,
            name=created.name,
            description=created.description,
            items_count=0,
            items=[],
            created_at=created.created_at,
        )

    async def delete_watchlist(self, watchlist_id: str, user_id: Optional[str] = None) -> bool:
        """Delete a user-owned watchlist."""
        wl = self.watchlist_repo.get_by_id_with_items(watchlist_id, user_id=user_id)
        if not wl:
            return False
        self.watchlist_repo.delete(wl)
        return True

    async def add_item(
        self,
        watchlist_id: str,
        symbol: str,
        user_id: Optional[str] = None,
    ) -> tuple[Optional[WatchlistItemDTO], bool]:
        """Add an asset to a user-owned watchlist by ticker symbol."""
        wl = self.watchlist_repo.get_by_id_with_items(watchlist_id, user_id=user_id)
        if not wl:
            return None, False

        clean_symbol = symbol.strip().upper()

        # 1. Look up or upsert instrument
        instrument = self.instrument_repo.get_by_symbol(clean_symbol)
        if not instrument:
            try:
                results = await self.market_data_service.search_instruments(clean_symbol)
                matched = next((p for p in results if p.symbol.upper() == clean_symbol), None)
                if matched:
                    instrument = self.instrument_repo.get_or_create_from_provider(matched)
                else:
                    quote = await self.market_data_service.get_quote(clean_symbol)
                    p_inst = ProviderInstrument(
                        symbol=clean_symbol,
                        name=clean_symbol,
                        currency=quote.currency,
                        asset_type="crypto" if "-USD" in clean_symbol else "equity",
                    )
                    instrument = self.instrument_repo.get_or_create_from_provider(p_inst)
            except Exception as ex:
                logger.error("Failed to resolve symbol %s for watchlist: %s", clean_symbol, ex)
                p_inst = ProviderInstrument(
                    symbol=clean_symbol,
                    name=clean_symbol,
                    currency="USD",
                    asset_type="crypto" if "-USD" in clean_symbol else "equity",
                )
                instrument = self.instrument_repo.get_or_create_from_provider(p_inst)

        # 2. Add instrument association to watchlist
        item, was_created = self.watchlist_repo.add_instrument(
            watchlist_id=watchlist_id,
            instrument_id=instrument.id,
        )

        # 3. Enrich with current quote
        dto = WatchlistItemDTO(
            id=item.id,
            instrument_id=instrument.id,
            symbol=instrument.symbol,
            name=instrument.name,
            currency=instrument.currency,
            exchange=instrument.exchange.code if instrument.exchange else None,
            asset_type=instrument.asset.asset_class if instrument.asset else None,
            added_at=item.added_at,
        )
        try:
            quote = await self.market_data_service.get_quote(instrument.symbol)
            dto.price = quote.price
            dto.change = quote.change
            dto.change_pct = quote.change_percent
            dto.is_up = quote.change >= 0 if quote.change is not None else True
        except Exception:
            pass

        return dto, was_created

    async def remove_item(
        self,
        watchlist_id: str,
        symbol_or_id: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """Remove an item from a user-owned watchlist."""
        wl = self.watchlist_repo.get_by_id_with_items(watchlist_id, user_id=user_id)
        if not wl:
            return False

        clean_target = symbol_or_id.strip()
        instrument = self.instrument_repo.get_by_symbol(clean_target.upper())
        instrument_id = instrument.id if instrument else clean_target

        return self.watchlist_repo.remove_instrument(
            watchlist_id=watchlist_id,
            instrument_id=instrument_id,
        )
