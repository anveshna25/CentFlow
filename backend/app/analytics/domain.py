from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


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


@dataclass(frozen=True)
class IndicatorSeries:
    """Time-indexed single indicator series with warmup handling."""

    name: str
    values: list[Optional[Decimal]]
    timestamps: Optional[list[datetime]] = None


@dataclass(frozen=True)
class MACDResult:
    """Moving Average Convergence Divergence component series."""

    macd_line: list[Optional[Decimal]]
    signal_line: list[Optional[Decimal]]
    histogram: list[Optional[Decimal]]
    fast_period: int = 12
    slow_period: int = 26
    signal_period: int = 9
    timestamps: Optional[list[datetime]] = None


@dataclass(frozen=True)
class BollingerBandsResult:
    """Bollinger Bands volatility envelope component series."""

    upper_band: list[Optional[Decimal]]
    middle_band: list[Optional[Decimal]]
    lower_band: list[Optional[Decimal]]
    bandwidth: list[Optional[Decimal]]
    percent_b: list[Optional[Decimal]]
    window: int = 20
    num_std: Decimal = Decimal("2.0")
    timestamps: Optional[list[datetime]] = None


class TrendPosture(str, Enum):
    """Directional trend alignment classification."""

    BULLISH = "bullish"
    MODERATELY_BULLISH = "moderately_bullish"
    NEUTRAL = "neutral"
    MODERATELY_BEARISH = "moderately_bearish"
    BEARISH = "bearish"
    GOLDEN_CROSS = "golden_cross"
    DEATH_CROSS = "death_cross"


class MomentumState(str, Enum):
    """Oscillator and momentum classification."""

    OVERBOUGHT = "overbought"
    BULLISH_MOMENTUM = "bullish_momentum"
    NEUTRAL = "neutral"
    BEARISH_MOMENTUM = "bearish_momentum"
    OVERSOLD = "oversold"


class VolatilityRegime(str, Enum):
    """Return dispersion and volatility regime classification."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass(frozen=True)
class MarketIntelligenceSummary:
    """Comprehensive, explainable technical intelligence report for an instrument."""

    symbol: str
    current_price: Decimal
    trend_posture: TrendPosture
    momentum_state: MomentumState
    volatility_regime: VolatilityRegime
    composite_score: int
    summary_verdict: str
    rationales: list[str]
    as_of: Optional[datetime] = None
    metrics: Optional[dict[str, Any]] = None
