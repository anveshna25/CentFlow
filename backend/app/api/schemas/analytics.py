from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from pydantic import Field

from app.api.schemas.base import BaseSchema


class PriceSummarySchema(BaseSchema):
    """Statistical summary of price series distribution."""

    current_price: Decimal = Field(..., description="Most recent price observation.")
    mean_price: Decimal = Field(..., description="Arithmetic mean price across period.")
    median_price: Decimal = Field(..., description="Median price across period.")
    min_price: Decimal = Field(..., description="Minimum price reached.")
    max_price: Decimal = Field(..., description="Maximum price reached.")
    data_points: int = Field(..., description="Total observation count.")


class PeriodReturnSchema(BaseSchema):
    """Return performance metrics over an observation window."""

    start_price: Decimal = Field(..., description="Initial price.")
    end_price: Decimal = Field(..., description="Terminal price.")
    absolute_change: Decimal = Field(..., description="Absolute price difference.")
    percentage_change: Decimal = Field(..., description="Percentage return over period.")
    log_return: Optional[Decimal] = Field(default=None, description="Continuously compounded log return.")
    start_time: Optional[datetime] = Field(default=None, description="Window start timestamp.")
    end_time: Optional[datetime] = Field(default=None, description="Window end timestamp.")


class VolatilityMetricsSchema(BaseSchema):
    """Historical return volatility and dispersion metrics."""

    sample_std: Decimal = Field(..., description="Sample standard deviation of periodic returns.")
    annualized_volatility: Decimal = Field(..., description="Scaled annualized volatility.")
    annualize_factor: int = Field(..., description="Annualization factor (252 for trading days, 365 for crypto).")
    sample_count: int = Field(..., description="Number of periodic returns evaluated.")


class DrawdownMetricSchema(BaseSchema):
    """Peak-to-trough decline metrics across an observation window."""

    peak_price: Decimal = Field(..., description="Highest preceding peak price.")
    trough_price: Decimal = Field(..., description="Lowest trough price during decline.")
    max_drawdown_amount: Decimal = Field(..., description="Absolute maximum decline.")
    max_drawdown_pct: Decimal = Field(..., description="Maximum decline percentage.")
    peak_index: int = Field(..., description="Index of the peak.")
    trough_index: int = Field(..., description="Index of the trough.")
    is_recovered: bool = Field(..., description="Whether terminal price has recovered to peak.")


class ReturnsAnalysisResponseSchema(BaseSchema):
    """Comprehensive performance and volatility analysis report."""

    symbol: str = Field(..., description="Instrument ticker symbol.")
    interval: str = Field(..., description="Bar timeframe interval.")
    lookback_days: int = Field(..., description="Observation window in days.")
    period_return: Optional[PeriodReturnSchema] = Field(default=None, description="Period return metrics.")
    volatility: VolatilityMetricsSchema = Field(..., description="Volatility metrics.")
    drawdown: DrawdownMetricSchema = Field(..., description="Maximum drawdown metrics.")
    summary: Optional[PriceSummarySchema] = Field(default=None, description="Price distribution summary.")


class MACDComponentSchema(BaseSchema):
    """MACD series arrays."""

    macd_line: list[Optional[Decimal]] = Field(..., description="Fast EMA minus Slow EMA series.")
    signal_line: list[Optional[Decimal]] = Field(..., description="Signal EMA series.")
    histogram: list[Optional[Decimal]] = Field(..., description="MACD histogram difference series.")
    fast_period: int = Field(default=12, description="Fast EMA period.")
    slow_period: int = Field(default=26, description="Slow EMA period.")
    signal_period: int = Field(default=9, description="Signal EMA period.")


class BollingerBandsComponentSchema(BaseSchema):
    """Bollinger Bands series arrays."""

    upper_band: list[Optional[Decimal]] = Field(..., description="Upper band series.")
    middle_band: list[Optional[Decimal]] = Field(..., description="Middle SMA band series.")
    lower_band: list[Optional[Decimal]] = Field(..., description="Lower band series.")
    bandwidth: list[Optional[Decimal]] = Field(..., description="Bandwidth percentage series.")
    percent_b: list[Optional[Decimal]] = Field(..., description="Percent B relative position series.")
    window: int = Field(default=20, description="Moving average lookback window.")
    num_std: Decimal = Field(default=Decimal("2.0"), description="Standard deviation multiplier.")


class IndicatorSeriesResponseSchema(BaseSchema):
    """Time-series technical indicators dataset."""

    symbol: str = Field(..., description="Instrument ticker symbol.")
    interval: str = Field(..., description="Bar timeframe interval.")
    lookback_days: int = Field(..., description="Lookback window in days.")
    timestamps: list[datetime] = Field(..., description="Aligned observation timestamps.")
    prices: list[Decimal] = Field(..., description="Aligned closing prices.")
    smas: dict[str, list[Optional[Decimal]]] = Field(default_factory=dict, description="Simple moving average series.")
    emas: dict[str, list[Optional[Decimal]]] = Field(default_factory=dict, description="Exponential moving average series.")
    rsi: Optional[list[Optional[Decimal]]] = Field(default=None, description="RSI 14 series.")
    macd: Optional[MACDComponentSchema] = Field(default=None, description="MACD component series.")
    bollinger: Optional[BollingerBandsComponentSchema] = Field(default=None, description="Bollinger Bands component series.")


class MarketIntelligenceResponseSchema(BaseSchema):
    """Synthesized explainable technical market intelligence report."""

    symbol: str = Field(..., description="Instrument ticker symbol.")
    current_price: Decimal = Field(..., description="Current instrument price.")
    trend_posture: str = Field(..., description="Classified trend posture (e.g. bullish, bearish, golden_cross).")
    momentum_state: str = Field(..., description="Classified momentum condition (e.g. overbought, bullish_momentum).")
    volatility_regime: str = Field(..., description="Classified volatility regime (e.g. low, normal, high, extreme).")
    composite_score: int = Field(..., description="Deterministic technical score between 0 and 100.")
    summary_verdict: str = Field(..., description="Plain-English technical verdict.")
    rationales: list[str] = Field(default_factory=list, description="List of transparent, explainable reasoning statements.")
    as_of: Optional[datetime] = Field(default=None, description="Observation timestamp.")
    metrics: Optional[dict[str, Any]] = Field(default=None, description="Raw technical metrics and indicator values.")
