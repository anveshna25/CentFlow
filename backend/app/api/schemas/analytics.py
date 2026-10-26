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


class RiskAdjustedMetricsSchema(BaseSchema):
    """Risk-adjusted return and distribution ratios."""

    annualized_return: Decimal = Field(..., description="Annualized percentage return.")
    cagr: Decimal = Field(..., description="Compound annual growth rate (%).")
    sharpe_ratio: Optional[Decimal] = Field(default=None, description="Annualized Sharpe ratio.")
    sortino_ratio: Optional[Decimal] = Field(default=None, description="Sortino downside risk ratio.")
    calmar_ratio: Optional[Decimal] = Field(default=None, description="Calmar drawdown recovery ratio.")
    downside_deviation: Decimal = Field(..., description="Annualized downside volatility deviation.")
    win_rate: Decimal = Field(..., description="Percentage of positive return periods.")
    best_return: Decimal = Field(..., description="Maximum single-period percentage return.")
    worst_return: Decimal = Field(..., description="Minimum single-period percentage return.")
    positive_periods: int = Field(..., description="Count of positive return periods.")
    negative_periods: int = Field(..., description="Count of negative return periods.")
    total_periods: int = Field(..., description="Total return periods evaluated.")


class BenchmarkMetricsSchema(BaseSchema):
    """Comparative benchmark metrics relative to a market index (e.g. SPY)."""

    benchmark_symbol: str = Field(..., description="Benchmark ticker symbol.")
    benchmark_return: Decimal = Field(..., description="Benchmark period percentage return.")
    excess_return: Decimal = Field(..., description="Asset return minus benchmark return (%).")
    beta: Optional[Decimal] = Field(default=None, description="Systematic market risk sensitivity (beta).")
    alpha: Optional[Decimal] = Field(default=None, description="Annualized Jensen's alpha (%).")
    correlation: Optional[Decimal] = Field(default=None, description="Pearson correlation coefficient.")
    r_squared: Optional[Decimal] = Field(default=None, description="Coefficient of determination (R^2).")
    tracking_error: Optional[Decimal] = Field(default=None, description="Annualized tracking error standard deviation.")
    information_ratio: Optional[Decimal] = Field(default=None, description="Information ratio relative to benchmark.")
    up_capture: Optional[Decimal] = Field(default=None, description="Upside capture ratio (%).")
    down_capture: Optional[Decimal] = Field(default=None, description="Downside capture ratio (%).")
    aligned_periods: int = Field(default=0, description="Number of timestamp-aligned trading sessions.")


class ReturnsAnalysisResponseSchema(BaseSchema):
    """Comprehensive performance and volatility analysis report."""

    symbol: str = Field(..., description="Instrument ticker symbol.")
    interval: str = Field(..., description="Bar timeframe interval.")
    lookback_days: int = Field(..., description="Observation window in days.")
    period_return: Optional[PeriodReturnSchema] = Field(default=None, description="Period return metrics.")
    volatility: VolatilityMetricsSchema = Field(..., description="Volatility metrics.")
    drawdown: DrawdownMetricSchema = Field(..., description="Maximum drawdown metrics.")
    summary: Optional[PriceSummarySchema] = Field(default=None, description="Price distribution summary.")
    risk_metrics: Optional[RiskAdjustedMetricsSchema] = Field(default=None, description="Risk-adjusted return ratios.")
    benchmark: Optional[BenchmarkMetricsSchema] = Field(default=None, description="Comparative benchmark metrics.")


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
