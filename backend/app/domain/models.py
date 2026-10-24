from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class Asset:
    """A tradable or trackable financial asset."""

    id: str
    name: str
    asset_type: str


@dataclass
class Exchange:
    """A marketplace or exchange where instruments are traded."""

    id: str
    name: str
    country: Optional[str] = None


@dataclass
class Market:
    """A market grouping in which instruments are tracked."""

    id: str
    name: str
    region: Optional[str] = None


@dataclass
class Instrument:
    """A specific financial instrument that can be priced or traded."""

    id: str
    symbol: str
    name: str
    asset: Asset
    exchange: Optional[Exchange] = None
    market: Optional[Market] = None


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