from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class Asset:
    """Canonical tradable or trackable financial asset entity."""

    id: str
    name: str
    asset_type: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


@dataclass
class Exchange:
    """A marketplace or exchange where instruments are traded."""

    id: str
    name: str
    code: Optional[str] = None
    mic: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    is_active: bool = True


@dataclass
class Market:
    """A market grouping in which instruments are tracked."""

    id: str
    name: str
    code: Optional[str] = None
    region: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


@dataclass
class Instrument:
    """Canonical financial instrument that can be priced, traded, or tracked."""

    id: str
    symbol: str
    name: str
    asset: Asset
    exchange: Optional[Exchange] = None
    market: Optional[Market] = None
    currency: str = "USD"
    provider_symbol: Optional[str] = None
    lot_size: Decimal = Decimal("1.0")
    is_active: bool = True

    @property
    def asset_type(self) -> str:
        """Asset class classification derived from underlying asset."""
        return self.asset.asset_type if self.asset else "equity"

    @property
    def sector(self) -> Optional[str]:
        """Industry sector derived from underlying asset."""
        return self.asset.sector if self.asset else None

    @property
    def industry(self) -> Optional[str]:
        """Industry subcategory derived from underlying asset."""
        return self.asset.industry if self.asset else None

    @property
    def country(self) -> Optional[str]:
        """Domicile or trading country derived from exchange or asset."""
        if self.exchange and self.exchange.country:
            return self.exchange.country
        return self.asset.country if self.asset else None

    @property
    def status(self) -> str:
        """Normalized operational status ('active' or 'inactive')."""
        return "active" if self.is_active else "inactive"


@dataclass
class Price:
    """A price observation for an instrument."""

    instrument: Instrument
    value: Decimal
    currency: str
    timestamp: datetime


@dataclass
class Watchlist:
    """A user-defined collection of instruments to monitor."""

    id: str
    name: str
    instruments: list[Instrument]


@dataclass
class Portfolio:
    """A collection of positions managed as a portfolio."""

    id: str
    name: str
    positions: list["Position"]


@dataclass
class Position:
    """A holding of an instrument within a portfolio."""

    instrument: Instrument
    quantity: Decimal
    average_price: Decimal
    currency: str