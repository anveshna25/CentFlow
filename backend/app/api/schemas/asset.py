"""Pydantic schemas for Asset Master and canonical Instrument data models."""

from decimal import Decimal
from typing import Optional
from pydantic import Field

from app.api.schemas.base import BaseSchema


class AssetSchema(BaseSchema):
    """Canonical asset representation schema."""

    id: str = Field(..., description="Unique asset identifier")
    name: str = Field(..., description="Canonical name of the asset")
    asset_type: str = Field(..., description="Asset class / category (e.g. equity, crypto, fx)")
    sector: Optional[str] = Field(default=None, description="Industry sector")
    industry: Optional[str] = Field(default=None, description="Specific industry classification")
    country: Optional[str] = Field(default=None, description="Country of origin")
    description: Optional[str] = Field(default=None, description="Business description")
    is_active: bool = Field(default=True, description="Whether asset is actively traded/tracked")


class ExchangeSchema(BaseSchema):
    """Trading exchange or venue schema."""

    id: str = Field(..., description="Unique exchange identifier")
    name: str = Field(..., description="Exchange name")
    code: Optional[str] = Field(default=None, description="Exchange code (e.g. NASDAQ, NYSE)")
    country: Optional[str] = Field(default=None, description="Operating country")
    country_code: Optional[str] = Field(default=None, description="Two-letter ISO country code")
    timezone: Optional[str] = Field(default=None, description="Trading venue timezone")
    currency: Optional[str] = Field(default=None, description="Primary settlement currency")
    is_active: bool = Field(default=True, description="Whether exchange is active")


class MarketSchema(BaseSchema):
    """Market grouping schema."""

    id: str = Field(..., description="Unique market identifier")
    name: str = Field(..., description="Market name")
    code: Optional[str] = Field(default=None, description="Market identifier code")
    region: Optional[str] = Field(default=None, description="Geographic or macroeconomic region")
    description: Optional[str] = Field(default=None, description="Market overview")
    is_active: bool = Field(default=True, description="Whether market is active")


class InstrumentDetailSchema(BaseSchema):
    """Canonical instrument response schema with full relational context."""

    id: str = Field(..., description="Unique instrument identifier")
    symbol: str = Field(..., description="Canonical ticker symbol")
    name: str = Field(..., description="Instrument display name")
    currency: str = Field(default="USD", description="Trading currency")
    provider_symbol: Optional[str] = Field(default=None, description="Associated provider symbol or ticker")
    lot_size: float = Field(default=1.0, description="Minimum lot trading size")
    is_active: bool = Field(default=True, description="Whether instrument is active")
    asset: AssetSchema = Field(..., description="Parent canonical asset")
    exchange: Optional[ExchangeSchema] = Field(default=None, description="Listing exchange")
    market: Optional[MarketSchema] = Field(default=None, description="Market segment")


class AssetDetailResponseSchema(BaseSchema):
    """Asset detail payload including all associated tradable instruments."""

    asset: AssetSchema = Field(..., description="Canonical asset details")
    instruments: list[InstrumentDetailSchema] = Field(
        default_factory=list, description="Instruments tied to this asset"
    )


class AssetEnrichRequestSchema(BaseSchema):
    """Request payload to enrich an asset's master metadata."""

    sector: Optional[str] = Field(default=None, description="Updated sector")
    industry: Optional[str] = Field(default=None, description="Updated industry")
    description: Optional[str] = Field(default=None, description="Updated asset description")


class AssetMasterSummarySchema(BaseSchema):
    """Summary metrics of the asset master database."""

    total_assets: int = Field(..., description="Total canonical assets")
    total_instruments: int = Field(..., description="Total instruments registered")
    active_instruments: int = Field(..., description="Total actively tradable instruments")
    sectors: list[str] = Field(default_factory=list, description="All registered sectors")
    asset_classes: list[str] = Field(default_factory=list, description="All registered asset classes")
