from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.database.models.asset import AssetModel
from app.repositories.base import BaseRepository


class AssetRepository(BaseRepository[AssetModel]):
    """Repository handling persistence operations for financial assets."""

    def __init__(self, db: Session):
        super().__init__(AssetModel, db)

    def get_by_name_and_class(self, name: str, asset_class: str) -> Optional[AssetModel]:
        """Lookup an asset by case-insensitive name and asset class."""
        stmt = select(AssetModel).where(
            func.lower(AssetModel.name) == name.strip().lower(),
            func.lower(AssetModel.asset_class) == asset_class.strip().lower(),
        )
        return self.db.scalars(stmt).first()

    def get_or_create(
        self,
        name: str,
        asset_class: str = "equity",
        description: Optional[str] = None,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
    ) -> AssetModel:
        """Retrieve an existing asset or persist a new one if not present."""
        clean_name = name.strip()
        clean_class = asset_class.strip().lower()
        existing = self.get_by_name_and_class(clean_name, clean_class)
        if existing:
            # Enrich fields if missing
            updated = False
            if sector and not existing.sector:
                existing.sector = sector
                updated = True
            if industry and not existing.industry:
                existing.industry = industry
                updated = True
            if description and not existing.description:
                existing.description = description
                updated = True
            if updated:
                self.update(existing)
            return existing

        asset = AssetModel(
            name=clean_name,
            asset_class=clean_class,
            description=description,
            sector=sector,
            industry=industry,
            is_active=True,
        )
        return self.create(asset)

    def list_assets(
        self,
        asset_class: Optional[str] = None,
        sector: Optional[str] = None,
        is_active: Optional[bool] = None,
        query: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[AssetModel]:
        """List assets matching criteria with pagination."""
        stmt = select(AssetModel)

        if asset_class:
            stmt = stmt.where(func.lower(AssetModel.asset_class) == asset_class.strip().lower())
        if sector:
            stmt = stmt.where(func.lower(AssetModel.sector) == sector.strip().lower())
        if is_active is not None:
            stmt = stmt.where(AssetModel.is_active == is_active)
        if query:
            clean_q = f"%{query.strip().lower()}%"
            stmt = stmt.where(
                func.lower(AssetModel.name).like(clean_q)
                | func.lower(AssetModel.description).like(clean_q)
            )

        stmt = stmt.order_by(AssetModel.name.asc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def count_assets(
        self,
        asset_class: Optional[str] = None,
        sector: Optional[str] = None,
        is_active: Optional[bool] = None,
        query: Optional[str] = None,
    ) -> int:
        """Count total assets matching criteria."""
        stmt = select(func.count(AssetModel.id))

        if asset_class:
            stmt = stmt.where(func.lower(AssetModel.asset_class) == asset_class.strip().lower())
        if sector:
            stmt = stmt.where(func.lower(AssetModel.sector) == sector.strip().lower())
        if is_active is not None:
            stmt = stmt.where(AssetModel.is_active == is_active)
        if query:
            clean_q = f"%{query.strip().lower()}%"
            stmt = stmt.where(
                func.lower(AssetModel.name).like(clean_q)
                | func.lower(AssetModel.description).like(clean_q)
            )

        return self.db.scalar(stmt) or 0

    def list_sectors(self) -> list[str]:
        """List distinct non-null sectors across assets."""
        stmt = (
            select(AssetModel.sector)
            .where(AssetModel.sector.isnot(None), AssetModel.sector != "")
            .distinct()
            .order_by(AssetModel.sector.asc())
        )
        return [s for s in self.db.scalars(stmt).all() if s]

    def list_asset_classes(self) -> list[str]:
        """List distinct asset classes."""
        stmt = select(AssetModel.asset_class).distinct().order_by(AssetModel.asset_class.asc())
        return [c for c in self.db.scalars(stmt).all() if c]
