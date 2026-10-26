"""Asset Master & Instrument Service providing canonical representation, resolution, and enrichment."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.database.models.instrument import InstrumentModel
from app.domain.models import Asset, Instrument
from app.repositories.asset import AssetRepository
from app.repositories.exchange import ExchangeRepository
from app.repositories.instrument import InstrumentRepository

logger = logging.getLogger(__name__)


@dataclass
class AssetMasterSummary:
    """Summary statistics of the asset master."""

    total_assets: int
    total_instruments: int
    active_instruments: int
    sectors: list[str]
    asset_classes: list[str]


class AssetMasterService:
    """Service layer managing canonical assets, instruments, symbol resolution, and enrichment."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.asset_repo = AssetRepository(db)
        self.instrument_repo = InstrumentRepository(db)
        self.exchange_repo = ExchangeRepository(db)

    def get_asset(self, asset_id: str) -> Optional[Asset]:
        """Retrieve canonical asset by its unique identifier."""
        model = self.asset_repo.get_by_id(asset_id)
        return model.to_domain() if model else None

    def get_asset_by_name(self, name: str, asset_class: str = "equity") -> Optional[Asset]:
        """Retrieve canonical asset by name and asset class."""
        model = self.asset_repo.get_by_name_and_class(name, asset_class)
        return model.to_domain() if model else None

    def list_assets(
        self,
        asset_class: Optional[str] = None,
        sector: Optional[str] = None,
        is_active: Optional[bool] = None,
        query: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Asset], int]:
        """List canonical assets with optional filtering, search, and pagination."""
        models = self.asset_repo.list_assets(
            asset_class=asset_class,
            sector=sector,
            is_active=is_active,
            query=query,
            offset=offset,
            limit=limit,
        )
        total = self.asset_repo.count_assets(
            asset_class=asset_class,
            sector=sector,
            is_active=is_active,
            query=query,
        )
        return [m.to_domain() for m in models], total

    def get_instrument(self, symbol_or_id: str) -> Optional[Instrument]:
        """Retrieve canonical instrument by symbol or ID with full relations."""
        model = self.instrument_repo.get_with_relations(symbol_or_id)
        return model.to_domain() if model else None

    def resolve_symbol(self, symbol_or_provider_symbol: str) -> Optional[Instrument]:
        """Resolve a symbol or provider ticker to canonical instrument domain model."""
        clean = symbol_or_provider_symbol.strip()
        # Direct lookup by symbol or ID
        inst = self.instrument_repo.get_with_relations(clean)
        if inst:
            return inst.to_domain()

        # Lookup by provider symbol/ticker
        inst = self.instrument_repo.get_by_provider_symbol(clean)
        if inst:
            return inst.to_domain()

        # Handle slash or dash representations (e.g. BTC-USD vs BTC/USD)
        alt_symbol = clean.replace("/", "-") if "/" in clean else clean.replace("-", "/")
        inst = self.instrument_repo.get_by_provider_symbol(alt_symbol)
        if inst:
            return inst.to_domain()

        return None

    def list_instruments(
        self,
        asset_id: Optional[str] = None,
        exchange_code: Optional[str] = None,
        active_only: bool = True,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Instrument]:
        """List instruments with joined asset, exchange, and market relations."""
        models = self.instrument_repo.list_with_relations(
            asset_id=asset_id,
            exchange_code=exchange_code,
            active_only=active_only,
            offset=offset,
            limit=limit,
        )
        return [m.to_domain() for m in models]

    def get_asset_with_instruments(self, asset_id: str) -> Optional[tuple[Asset, list[Instrument]]]:
        """Retrieve asset along with all associated instruments."""
        asset_model = self.asset_repo.get_by_id(asset_id)
        if not asset_model:
            return None
        instruments = self.instrument_repo.list_by_asset(asset_id, active_only=False)
        return asset_model.to_domain(), [inst.to_domain() for inst in instruments]

    def enrich_asset_metadata(
        self,
        asset_id: str,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[Asset]:
        """Enrich metadata for an existing asset."""
        asset = self.asset_repo.get_by_id(asset_id)
        if not asset:
            return None

        updated = False
        if sector is not None and asset.sector != sector:
            asset.sector = sector
            updated = True
        if industry is not None and asset.industry != industry:
            asset.industry = industry
            updated = True
        if description is not None and asset.description != description:
            asset.description = description
            updated = True

        if updated:
            self.asset_repo.update(asset)
            logger.info("Enriched asset %s (%s) metadata", asset.id, asset.name)

        return asset.to_domain()

    def register_instrument(
        self,
        symbol: str,
        name: str,
        asset_name: str,
        asset_class: str = "equity",
        exchange_code: Optional[str] = None,
        currency: str = "USD",
        lot_size: Decimal = Decimal("1.0"),
        provider_symbol: Optional[str] = None,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Instrument:
        """Register or update a canonical instrument and associate with canonical asset."""
        clean_symbol = symbol.strip().upper()
        existing = self.instrument_repo.get_with_relations(clean_symbol)
        if existing:
            # Sync metadata if needed
            updated = False
            if name and existing.name != name:
                existing.name = name
                updated = True
            if provider_symbol and existing.ticker != provider_symbol:
                existing.ticker = provider_symbol
                updated = True
            if updated:
                self.instrument_repo.update(existing)
            return existing.to_domain()

        # Get or create parent asset
        asset = self.asset_repo.get_or_create(
            name=asset_name.strip(),
            asset_class=asset_class.strip().lower(),
            description=description,
            sector=sector,
            industry=industry,
        )

        exchange = None
        if exchange_code:
            exchange = self.exchange_repo.get_or_create(code=exchange_code.strip().upper())

        instrument_model = InstrumentModel(
            asset_id=asset.id,
            exchange_id=exchange.id if exchange else None,
            symbol=clean_symbol,
            ticker=provider_symbol or clean_symbol,
            name=name.strip(),
            currency=currency.strip().upper(),
            lot_size=lot_size,
            is_active=True,
        )
        saved = self.instrument_repo.create(instrument_model)
        full = self.instrument_repo.get_with_relations(saved.id)
        return full.to_domain() if full else saved.to_domain()

    def get_summary(self) -> AssetMasterSummary:
        """Return master data catalog summary metrics."""
        total_assets = self.asset_repo.count_assets()
        all_instruments = self.instrument_repo.list_with_relations(limit=10000)
        active_instruments = sum(1 for i in all_instruments if i.is_active)
        sectors = self.asset_repo.list_sectors()
        asset_classes = self.asset_repo.list_asset_classes()

        return AssetMasterSummary(
            total_assets=total_assets,
            total_instruments=len(all_instruments),
            active_instruments=active_instruments,
            sectors=sectors,
            asset_classes=asset_classes,
        )
