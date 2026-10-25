from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import Field
from app.api.schemas.base import BaseSchema


class WatchlistCreateRequest(BaseSchema):
    """Payload to create a new user watchlist."""

    name: str = Field(..., min_length=1, max_length=100, description="Watchlist name.")
    description: Optional[str] = Field(default=None, max_length=500, description="Optional description.")


class WatchlistAddSymbolRequest(BaseSchema):
    """Payload to add a symbol to an existing watchlist."""

    symbol: str = Field(..., min_length=1, max_length=50, description="Instrument ticker symbol (e.g. AAPL, BTC-USD).")


class WatchlistItemResponseSchema(BaseSchema):
    """Schema representing an instrument entry in a watchlist."""

    id: str = Field(..., description="Unique entry association ID.")
    instrument_id: str = Field(..., description="Instrument database ID.")
    symbol: str = Field(..., description="Ticker symbol.")
    name: str = Field(..., description="Asset name.")
    currency: str = Field(..., description="Trading currency.")
    exchange: Optional[str] = Field(default=None, description="Listing exchange code.")
    asset_type: Optional[str] = Field(default=None, description="Asset class classification.")
    added_at: datetime = Field(..., description="Timestamp when item was added.")
    price: Optional[Decimal] = Field(default=None, description="Latest market price.")
    change: Optional[Decimal] = Field(default=None, description="Absolute 24h price change.")
    change_pct: Optional[Decimal] = Field(default=None, description="Percentage 24h price change.")
    is_up: Optional[bool] = Field(default=None, description="True if price change is non-negative.")


class WatchlistResponseSchema(BaseSchema):
    """Detailed watchlist schema containing all item entries."""

    id: str = Field(..., description="Watchlist ID.")
    name: str = Field(..., description="Watchlist name.")
    description: Optional[str] = Field(default=None, description="Watchlist description.")
    items_count: int = Field(default=0, description="Number of tracked items.")
    items: list[WatchlistItemResponseSchema] = Field(default_factory=list, description="Tracked instrument items.")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp.")


class WatchlistSummaryResponseSchema(BaseSchema):
    """Lightweight summary schema for catalog listing of watchlists."""

    id: str = Field(..., description="Watchlist ID.")
    name: str = Field(..., description="Watchlist name.")
    description: Optional[str] = Field(default=None, description="Watchlist description.")
    items_count: int = Field(default=0, description="Number of tracked items.")
    symbols: list[str] = Field(default_factory=list, description="Preview of tracked symbols.")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp.")
