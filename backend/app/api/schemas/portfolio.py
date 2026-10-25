from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import Field
from app.api.schemas.base import BaseSchema


class PositionCreateRequest(BaseSchema):
    """Payload to add or accumulate a position in a portfolio."""

    symbol: str = Field(..., description="Instrument ticker symbol (e.g. AAPL, BTC-USD).", min_length=1, max_length=20)
    quantity: Decimal = Field(..., description="Position quantity/units held.", gt=0)
    average_price: Decimal = Field(..., description="Average acquisition cost basis per unit in currency.", ge=0)
    currency: str = Field(default="USD", description="Currency ISO code.", min_length=3, max_length=3)


class PositionResponse(BaseSchema):
    """Detailed position holdings breakdown."""

    id: str = Field(..., description="Unique position identifier.")
    instrument_id: str = Field(..., description="Associated instrument ID.")
    symbol: str = Field(..., description="Instrument ticker symbol.")
    name: str = Field(..., description="Instrument or asset name.")
    asset_type: str = Field(..., description="Asset class category (equity, crypto, etf).")
    quantity: Decimal = Field(..., description="Current position quantity.")
    average_price: Decimal = Field(..., description="Average entry cost basis per unit.")
    current_price: Decimal = Field(..., description="Current market price per unit from market data provider.")
    cost_basis: Decimal = Field(..., description="Total cost basis (quantity * average_price).")
    market_value: Decimal = Field(..., description="Total current market value (quantity * current_price).")
    unrealized_pnl: Decimal = Field(..., description="Unrealized dollar gain/loss (market_value - cost_basis).")
    unrealized_pnl_percent: Decimal = Field(..., description="Unrealized percentage gain/loss.")
    currency: str = Field(default="USD", description="Quoted position currency.")
    opened_at: Optional[datetime] = Field(default=None, description="Timestamp when position was created.")


class PortfolioCreateRequest(BaseSchema):
    """Payload to create an investment portfolio."""

    name: str = Field(..., description="Human-readable portfolio name.", min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, description="Optional portfolio description.")
    base_currency: str = Field(default="USD", description="Portfolio base reporting currency.", min_length=3, max_length=3)


class PortfolioResponse(BaseSchema):
    """Detailed portfolio representation including calculated aggregate valuations."""

    id: str = Field(..., description="Unique portfolio identifier.")
    name: str = Field(..., description="Portfolio name.")
    description: Optional[str] = Field(default=None, description="Portfolio description.")
    base_currency: str = Field(default="USD", description="Base reporting currency.")
    total_valuation: Decimal = Field(..., description="Aggregate current market value across all open positions.")
    total_cost_basis: Decimal = Field(..., description="Aggregate invested capital / cost basis.")
    total_unrealized_pnl: Decimal = Field(..., description="Total unrealized gain/loss ($).")
    total_unrealized_pnl_percent: Decimal = Field(..., description="Total unrealized gain/loss (%).")
    positions_count: int = Field(default=0, description="Total number of positions.")
    positions: list[PositionResponse] = Field(default_factory=list, description="List of individual holdings.")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp.")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp.")
