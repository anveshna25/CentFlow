from dataclasses import asdict
from typing import Any, Optional


from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.routes.market_data import get_market_data_service
from app.api.schemas.analytics import (
    ATRComponentSchema,
    BenchmarkMetricsSchema,
    BollingerBandsComponentSchema,
    DrawdownMetricSchema,
    IndicatorSeriesResponseSchema,
    MACDComponentSchema,
    MarketIntelligenceResponseSchema,
    PeriodReturnSchema,
    PriceSummarySchema,
    ReturnsAnalysisResponseSchema,
    RiskAdjustedMetricsSchema,
    VolatilityMetricsSchema,
)
from app.api.schemas.base import ResponseEnvelope
from app.database.session import get_db
from app.services.analytics import AnalyticsService
from app.services.market_data import MarketDataService

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_analytics_service(
    db: Session = Depends(get_db),
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> AnalyticsService:
    """Dependency injector for AnalyticsService."""
    return AnalyticsService(market_data_service=market_data_service, db=db)


def _resolve_val(val: Any, default: Any) -> Any:
    """Helper to unwrap FastAPI Query default if invoked as a plain function in tests."""
    if hasattr(val, "default"):
        return val.default
    return val if val is not None else default


@router.get("/summary/{symbol}", response_model=ResponseEnvelope[MarketIntelligenceResponseSchema])
async def get_analytics_summary(
    symbol: str,
    interval: str = Query(default="1d", description="Observation bar interval."),
    lookback_days: int = Query(default=365, ge=1, le=1825, description="Lookback window in days."),
    service: AnalyticsService = Depends(get_analytics_service),
) -> ResponseEnvelope[MarketIntelligenceResponseSchema]:
    """Retrieve synthesized explainable market intelligence and technical posture for a symbol."""
    resolved_interval = _resolve_val(interval, "1d")
    resolved_lookback = _resolve_val(lookback_days, 365)
    intel = await service.get_market_intelligence(
        symbol=symbol,
        interval=resolved_interval,
        lookback_days=resolved_lookback,
    )


    data = MarketIntelligenceResponseSchema(
        symbol=intel.symbol,
        current_price=intel.current_price,
        trend_posture=intel.trend_posture.value,
        momentum_state=intel.momentum_state.value,
        volatility_regime=intel.volatility_regime.value,
        composite_score=intel.composite_score,
        summary_verdict=intel.summary_verdict,
        rationales=intel.rationales,
        as_of=intel.as_of,
        metrics=intel.metrics,
    )
    return ResponseEnvelope(
        data=data,
        meta={"symbol": symbol.strip().upper(), "interval": interval, "lookback_days": lookback_days},
    )


@router.get("/indicators/{symbol}", response_model=ResponseEnvelope[IndicatorSeriesResponseSchema])
async def get_indicators(
    symbol: str,
    interval: str = Query(default="1d", description="Observation bar interval."),
    lookback_days: int = Query(default=365, ge=1, le=1825, description="Lookback window in days."),
    include_rsi: bool = Query(default=True, description="Whether to include RSI 14."),
    include_macd: bool = Query(default=True, description="Whether to include MACD (12, 26, 9)."),
    include_bollinger: bool = Query(default=True, description="Whether to include Bollinger Bands (20, 2.0)."),
    include_atr: bool = Query(default=True, description="Whether to include Average True Range (ATR 14)."),
    service: AnalyticsService = Depends(get_analytics_service),
) -> ResponseEnvelope[IndicatorSeriesResponseSchema]:
    """Retrieve full aligned technical indicator time series dataset."""
    resolved_interval = _resolve_val(interval, "1d")
    resolved_lookback = _resolve_val(lookback_days, 365)
    include_rsi_bool = _resolve_val(include_rsi, True)
    include_macd_bool = _resolve_val(include_macd, True)
    include_bollinger_bool = _resolve_val(include_bollinger, True)
    include_atr_bool = _resolve_val(include_atr, True)

    result = await service.get_technical_indicators(
        symbol=symbol,
        interval=resolved_interval,
        lookback_days=resolved_lookback,
        include_rsi=include_rsi_bool,
        include_macd=include_macd_bool,
        include_bollinger=include_bollinger_bool,
        include_atr=include_atr_bool,
    )

    macd_schema = None
    if result.get("macd"):
        m = result["macd"]
        macd_schema = MACDComponentSchema(
            macd_line=m.macd_line,
            signal_line=m.signal_line,
            histogram=m.histogram,
            fast_period=m.fast_period,
            slow_period=m.slow_period,
            signal_period=m.signal_period,
        )

    bb_schema = None
    if result.get("bollinger"):
        b = result["bollinger"]
        bb_schema = BollingerBandsComponentSchema(
            upper_band=b.upper_band,
            middle_band=b.middle_band,
            lower_band=b.lower_band,
            bandwidth=b.bandwidth,
            percent_b=b.percent_b,
            window=b.window,
            num_std=b.num_std,
        )

    atr_schema = None
    if result.get("atr"):
        a = result["atr"]
        atr_schema = ATRComponentSchema(
            tr=a.tr,
            atr=a.atr,
            atr_percent=a.atr_percent,
            period=a.period,
        )

    data = IndicatorSeriesResponseSchema(
        symbol=result["symbol"],
        interval=resolved_interval,
        lookback_days=resolved_lookback,
        timestamps=result["timestamps"],
        prices=result["prices"],
        smas=result["smas"],
        emas=result["emas"],
        rsi=result["rsi"],
        macd=macd_schema,
        bollinger=bb_schema,
        atr=atr_schema,
    )
    return ResponseEnvelope(
        data=data,
        meta={"symbol": symbol.strip().upper(), "interval": resolved_interval, "points": len(result["prices"])},
    )


@router.get("/returns/{symbol}", response_model=ResponseEnvelope[ReturnsAnalysisResponseSchema])
async def get_returns_analysis(
    symbol: str,
    interval: str = Query(default="1d", description="Observation bar interval."),
    lookback_days: int = Query(default=365, ge=1, le=1825, description="Lookback window in days."),
    annualize_factor: int = Query(default=252, description="Annualization factor (252 stocks, 365 crypto)."),
    benchmark: Optional[str] = Query(default=None, description="Optional benchmark index symbol (e.g. SPY, QQQ, BTC-USD) for comparative beta, alpha, and correlation."),
    risk_free_rate: float = Query(default=0.0, ge=0.0, le=1.0, description="Annual risk-free benchmark rate for Sharpe and Sortino ratios."),
    service: AnalyticsService = Depends(get_analytics_service),
) -> ResponseEnvelope[ReturnsAnalysisResponseSchema]:
    """Retrieve return performance, statistical distribution, volatility, drawdown, and benchmark analysis."""
    resolved_interval = _resolve_val(interval, "1d")
    resolved_lookback = _resolve_val(lookback_days, 365)
    resolved_annualize = _resolve_val(annualize_factor, 252)
    resolved_benchmark = _resolve_val(benchmark, None)
    resolved_rf = _resolve_val(risk_free_rate, 0.0)

    result = await service.get_performance_metrics(
        symbol=symbol,
        interval=resolved_interval,
        lookback_days=resolved_lookback,
        annualize_factor=resolved_annualize,
        benchmark_symbol=resolved_benchmark,
        risk_free_rate=resolved_rf,
    )

    pr = result.get("period_return")
    pr_schema = PeriodReturnSchema(**asdict(pr)) if pr else None

    vol = result["volatility"]
    vol_schema = VolatilityMetricsSchema(**asdict(vol))

    dd = result["drawdown"]
    dd_schema = DrawdownMetricSchema(**asdict(dd))

    sumry = result.get("summary")
    sumry_schema = PriceSummarySchema(**asdict(sumry)) if sumry else None

    risk_m = result.get("risk_metrics")
    risk_schema = RiskAdjustedMetricsSchema(**asdict(risk_m)) if risk_m else None

    bench_m = result.get("benchmark")
    bench_schema = BenchmarkMetricsSchema(**asdict(bench_m)) if bench_m else None

    data = ReturnsAnalysisResponseSchema(
        symbol=result["symbol"],
        interval=result["interval"],
        lookback_days=result["lookback_days"],
        period_return=pr_schema,
        volatility=vol_schema,
        drawdown=dd_schema,
        summary=sumry_schema,
        risk_metrics=risk_schema,
        benchmark=bench_schema,
    )
    meta_info: dict[str, Any] = {
        "symbol": symbol.strip().upper(),
        "interval": resolved_interval,
        "lookback_days": resolved_lookback,
    }
    if resolved_benchmark:
        meta_info["benchmark"] = resolved_benchmark.strip().upper()

    return ResponseEnvelope(
        data=data,
        meta=meta_info,
    )
