from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class CalculationPeriod(str, Enum):
    """Standardized analytical observation windows."""

    ONE_DAY = "1d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1m"
    THREE_MONTHS = "3m"
    SIX_MONTHS = "6m"
    ONE_YEAR = "1y"
    YEAR_TO_DATE = "ytd"
    ALL = "all"


@dataclass(frozen=True)
class PeriodReturn:
    """Statistical return performance over an observation window."""

    start_price: Decimal
    end_price: Decimal
    absolute_change: Decimal
    percentage_change: Decimal
    log_return: Optional[Decimal] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


@dataclass(frozen=True)
class VolatilityMetrics:
    """Historical return volatility and dispersion metrics."""

    sample_std: Decimal
    annualized_volatility: Decimal
    annualize_factor: int
    sample_count: int


@dataclass(frozen=True)
class DrawdownMetric:
    """Peak-to-trough decline metrics across an observation series."""

    peak_price: Decimal
    trough_price: Decimal
    max_drawdown_amount: Decimal
    max_drawdown_pct: Decimal
    peak_index: int
    trough_index: int
    is_recovered: bool


@dataclass(frozen=True)
class PriceSeriesSummary:
    """Fundamental statistical summary of a price series."""

    current_price: Decimal
    mean_price: Decimal
    median_price: Decimal
    min_price: Decimal
    max_price: Decimal
    data_points: int
