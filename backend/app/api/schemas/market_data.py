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


class ProviderStatusSchema(BaseSchema):
    """Market data provider diagnostic status schema."""

    name: str = Field(..., description="Provider identifier.")
    is_active: bool = Field(..., description="Whether provider is online and operational.")
    message: Optional[str] = Field(default=None, description="Optional diagnostic message.")
