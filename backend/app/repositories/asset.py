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
