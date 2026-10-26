from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import Field
from app.api.schemas.base import BaseSchema


class QuoteResponseSchema(BaseSchema):
    """Normalized price quote schema for API responses."""

    symbol: str = Field(..., description="Instrument ticker symbol.")
    price: Decimal = Field(..., description="Current observation price.")
    currency: str = Field(..., description="Currency of quote.")
    timestamp: datetime = Field(..., description="Timestamp of quote in UTC.")
    volume: Optional[Decimal] = Field(default=None, description="24h trading volume.")
    open: Optional[Decimal] = Field(default=None, description="Opening price.")
    high: Optional[Decimal] = Field(default=None, description="High price.")
    low: Optional[Decimal] = Field(default=None, description="Low price.")
    previous_close: Optional[Decimal] = Field(default=None, description="Previous session closing price.")
    change: Optional[Decimal] = Field(default=None, description="Absolute change.")
    change_percent: Optional[Decimal] = Field(default=None, description="Percentage change.")
    market_status: Optional[str] = Field(default="UNKNOWN", description="Market session status: OPEN, CLOSED, EXTENDED, UNKNOWN.")
    is_stale: bool = Field(default=False, description="Whether the quote observation is stale.")
    delay_minutes: int = Field(default=0, description="Provider data delay in minutes (0 for real-time).")
    data_source: Optional[str] = Field(default=None, description="Source market data provider identifier.")
    staleness_seconds: Optional[int] = Field(default=None, description="Elapsed seconds since quote timestamp.")


class BarResponseSchema(BaseSchema):
    """Historical OHLCV candle bar schema for API responses."""

    symbol: str = Field(..., description="Instrument ticker symbol.")
    timestamp: datetime = Field(..., description="Bar interval timestamp.")
    open: Decimal = Field(..., description="Opening price.")
    high: Decimal = Field(..., description="High price.")
    low: Decimal = Field(..., description="Low price.")
    close: Decimal = Field(..., description="Closing price.")
    volume: Decimal = Field(..., description="Volume traded.")


class InstrumentResponseSchema(BaseSchema):
    """Instrument metadata schema for search API responses."""

    symbol: str = Field(..., description="Ticker symbol.")
    name: str = Field(..., description="Entity full name.")
    asset_type: str = Field(..., description="Asset class classification.")
    currency: Optional[str] = Field(default=None, description="Quote currency.")
    exchange: Optional[str] = Field(default=None, description="Listing exchange venue.")
    market: Optional[str] = Field(default=None, description="Market grouping.")


class ProviderCapabilitiesSchema(BaseSchema):
    """Operational capabilities schema for a market data provider."""

    supported_intervals: list[str] = Field(default_factory=lambda: ["1d"], description="Supported timeframe bar intervals.")
    supports_search: bool = Field(default=True, description="Whether instrument search is supported.")
    supports_realtime: bool = Field(default=True, description="Whether real-time data is supported.")
    is_delayed: bool = Field(default=False, description="Whether quotes/bars are delayed.")
    delay_minutes: int = Field(default=0, description="Delay duration in minutes if delayed.")


class ProviderStatusSchema(BaseSchema):
    """Market data provider diagnostic status schema."""

    name: str = Field(..., description="Provider identifier.")
    is_active: bool = Field(..., description="Whether provider is online and operational.")
    message: Optional[str] = Field(default=None, description="Optional diagnostic message.")
    latency_ms: Optional[float] = Field(default=None, description="Round-trip latency in milliseconds.")
    capabilities: Optional[ProviderCapabilitiesSchema] = Field(default=None, description="Provider capabilities.")


class PersistedPriceSchema(BaseSchema):
    """Schema representing a durable market price observation from the database."""

    id: str = Field(..., description="Observation unique identifier.")
    instrument_id: str = Field(..., description="Associated instrument ID.")
    timestamp: datetime = Field(..., description="Price timestamp in UTC.")
    price: Decimal = Field(..., description="Observation or close price.")
    open: Optional[Decimal] = Field(default=None, description="Open price if applicable.")
    high: Optional[Decimal] = Field(default=None, description="High price if applicable.")
    low: Optional[Decimal] = Field(default=None, description="Low price if applicable.")
    close: Optional[Decimal] = Field(default=None, description="Close price if applicable.")
    volume: Optional[Decimal] = Field(default=None, description="Volume if applicable.")
    currency: str = Field(..., description="Denominated currency.")
    interval: str = Field(..., description="Observation interval ('tick', '1d', etc.).")
    source: Optional[str] = Field(default=None, description="Source provider identifier.")
    created_at: Optional[datetime] = Field(default=None, description="Record creation timestamp.")


class BackfillRequestSchema(BaseSchema):
    """Request payload for triggering historical bar backfill."""

    days: int = Field(default=30, ge=1, le=365, description="Number of past days to backfill.")
    interval: str = Field(default="1d", description="Aggregation interval (e.g., '1d', '1h').")
    start: Optional[datetime] = Field(default=None, description="Optional explicit start timestamp.")
    end: Optional[datetime] = Field(default=None, description="Optional explicit end timestamp.")


class BackfillResponseSchema(BaseSchema):
    """Summary of backfilled historical price bars."""

    symbol: str = Field(..., description="Instrument symbol backfilled.")
    instrument_id: str = Field(..., description="Database instrument ID.")
    bars_ingested: int = Field(..., description="Count of newly persisted bars.")
    interval: str = Field(..., description="Aggregation interval.")
    source: str = Field(..., description="Provider source identifier.")


class SyncCatalogRequestSchema(BaseSchema):
    """Request payload for searching and synchronizing instrument catalog."""

    query: str = Field(..., min_length=1, description="Symbol or name keyword.")


class SyncCatalogResponseSchema(BaseSchema):
    """Response summary of synced catalog instruments."""

    query: str = Field(..., description="Query executed.")
    synced_count: int = Field(..., description="Number of instruments discovered and persisted.")
    instruments: list[InstrumentResponseSchema] = Field(..., description="List of instruments synced.")
