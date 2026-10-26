from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.analytics.calculations import (
    align_price_series,
    calculate_benchmark_metrics,
    calculate_drawdowns,
    calculate_period_return,
    calculate_price_summary,
    calculate_returns,
    calculate_risk_adjusted_metrics,
    calculate_rolling_volatility,
    prepare_validated_series,
    to_decimal,
)
from app.analytics.domain import (
    ATRResult,
    BenchmarkMetrics,
    BollingerBandsResult,
    DrawdownMetric,
    MACDResult,
    MarketIntelligenceSummary,
    PeriodReturn,
    PriceSeriesSummary,
    RiskAdjustedMetrics,
    VolatilityMetrics,
)
from app.analytics.indicators import (
    calculate_atr,
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
    calculate_true_range,
)
from app.analytics.intelligence import synthesize_market_intelligence
from app.repositories.instrument import InstrumentRepository
from app.repositories.price import PriceRepository
from app.services.market_data import MarketDataService


class AnalyticsService:
    """Service layer orchestrating market intelligence and quantitative analytics.

    Coordinates retrieval of historical price series from persisted database
    repositories or active market-data providers, executes mathematical
    indicators, and synthesizes explainable market intelligence.
    """

    def __init__(
        self,
        market_data_service: Optional[MarketDataService] = None,
        db: Optional[Session] = None,
    ) -> None:
        self._market_data_service = market_data_service or MarketDataService()
        self._db = db
        self._price_repo = PriceRepository(db) if db else None
        self._instrument_repo = InstrumentRepository(db) if db else None

    async def get_price_series(
        self,
        symbol: str,
        interval: str = "1d",
        lookback_days: int = 365,
    ) -> tuple[list[Decimal], list[datetime]]:
        """Retrieve chronological closing prices and timestamps for a symbol."""
        clean_symbol = symbol.strip().upper()
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=lookback_days)

        raw_prices: list[Decimal] = []
        raw_timestamps: list[datetime] = []

        # 1. If database session is present, attempt to query persisted prices
        if self._db and self._price_repo and self._instrument_repo:
            instrument = self._instrument_repo.get_by_symbol(clean_symbol)
            if instrument:
                prices_models = self._price_repo.get_historical_prices(
                    instrument_id=instrument.id,
                    start=start,
                    end=now,
                    interval=interval,
                )
                if len(prices_models) >= 10:  # Valid series in DB
                    raw_prices = [to_decimal(m.close or m.value) for m in prices_models]
                    raw_timestamps = [m.timestamp for m in prices_models]

        # 2. Query market data service (provider/cache) if DB was empty or incomplete
        if not raw_prices:
            bars = await self._market_data_service.get_historical_bars(
                symbol=clean_symbol,
                start=start,
                end=now,
                interval=interval,
            )
            raw_prices = [to_decimal(b.close) for b in bars]
            raw_timestamps = [b.timestamp for b in bars]

        # Clean, deduplicate timestamps, sort, and handle gaps with exact precision
        return prepare_validated_series(raw_prices, raw_timestamps)

    async def get_ohlcv_series(
        self,
        symbol: str,
        interval: str = "1d",
        lookback_days: int = 365,
    ) -> tuple[list[Decimal], list[Decimal], list[Decimal], list[Decimal], list[datetime]]:
        """Retrieve chronological High, Low, Close prices, Volumes, and Timestamps for a symbol."""
        clean_symbol = symbol.strip().upper()
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=lookback_days)

        # 1. Check database persistence
        if self._db and self._price_repo and self._instrument_repo:
            instrument = self._instrument_repo.get_by_symbol(clean_symbol)
            if instrument:
                prices_models = self._price_repo.get_historical_prices(
                    instrument_id=instrument.id,
                    start=start,
                    end=now,
                    interval=interval,
                )
                if len(prices_models) >= 10:
                    highs = [to_decimal(m.high if m.high is not None else (m.close or m.value)) for m in prices_models]
                    lows = [to_decimal(m.low if m.low is not None else (m.close or m.value)) for m in prices_models]
                    closes = [to_decimal(m.close if m.close is not None else m.value) for m in prices_models]
                    volumes = [to_decimal(m.volume if m.volume is not None else 0) for m in prices_models]
                    timestamps = [m.timestamp for m in prices_models]
                    return highs, lows, closes, volumes, timestamps

        # 2. Query market data provider / cache
        bars = await self._market_data_service.get_historical_bars(
            symbol=clean_symbol,
            start=start,
            end=now,
            interval=interval,
        )

        highs = [to_decimal(b.high if b.high is not None else b.close) for b in bars]
        lows = [to_decimal(b.low if b.low is not None else b.close) for b in bars]
        closes = [to_decimal(b.close) for b in bars]
        volumes = [to_decimal(b.volume if b.volume is not None else 0) for b in bars]
        timestamps = [b.timestamp for b in bars]
        return highs, lows, closes, volumes, timestamps

    async def get_price_summary(
        self,
        symbol: str,
        interval: str = "1d",
        lookback_days: int = 365,
    ) -> Optional[PriceSeriesSummary]:
        """Compute statistical price distribution summary for a symbol."""
        prices, _ = await self.get_price_series(symbol, interval, lookback_days)
        return calculate_price_summary(prices)

    async def get_performance_metrics(
        self,
        symbol: str,
        interval: str = "1d",
        lookback_days: int = 365,
        annualize_factor: int = 252,
        benchmark_symbol: Optional[str] = None,
        risk_free_rate: float = 0.0,
    ) -> dict[str, Any]:
        """Compute performance returns, drawdowns, volatility, risk-adjusted metrics, and benchmark analysis."""
        clean_symbol = symbol.strip().upper()
        prices, timestamps = await self.get_price_series(clean_symbol, interval, lookback_days)

        period_return = calculate_period_return(prices, timestamps)
        returns = calculate_returns(prices)
        volatility = calculate_rolling_volatility(returns, annualize_factor=annualize_factor)
        drawdown = calculate_drawdowns(prices)
        summary = calculate_price_summary(prices)
        risk_metrics = calculate_risk_adjusted_metrics(
            prices=prices,
            returns=returns,
            volatility=volatility,
            drawdown=drawdown,
            risk_free_rate=risk_free_rate,
            annualize_factor=annualize_factor,
        )

        benchmark_metrics: Optional[BenchmarkMetrics] = None
        if benchmark_symbol and benchmark_symbol.strip():
            clean_bench = benchmark_symbol.strip().upper()
            try:
                bench_prices, bench_timestamps = await self.get_price_series(
                    clean_bench, interval, lookback_days
                )
                aligned_asset, aligned_bench, _ = align_price_series(
                    prices, timestamps, bench_prices, bench_timestamps
                )
                if len(aligned_asset) >= 2 and len(aligned_bench) >= 2:
                    benchmark_metrics = calculate_benchmark_metrics(
                        benchmark_symbol=clean_bench,
                        asset_prices=aligned_asset,
                        benchmark_prices=aligned_bench,
                        annualize_factor=annualize_factor,
                    )
            except Exception:
                pass

        return {
            "symbol": clean_symbol,
            "interval": interval,
            "lookback_days": lookback_days,
            "period_return": period_return,
            "volatility": volatility,
            "drawdown": drawdown,
            "summary": summary,
            "risk_metrics": risk_metrics,
            "benchmark": benchmark_metrics,
        }

    async def get_technical_indicators(
        self,
        symbol: str,
        interval: str = "1d",
        lookback_days: int = 365,
        sma_windows: Optional[Sequence[int]] = None,
        ema_windows: Optional[Sequence[int]] = None,
        include_rsi: bool = True,
        include_macd: bool = True,
        include_bollinger: bool = True,
        include_atr: bool = True,
        atr_period: int = 14,
    ) -> dict[str, Any]:
        """Compute technical indicator series for a symbol."""
        highs, lows, prices, _, timestamps = await self.get_ohlcv_series(symbol, interval, lookback_days)

        smas: dict[str, list[Optional[Decimal]]] = {}
        for w in (sma_windows or [20, 50, 200]):
            smas[f"sma_{w}"] = calculate_sma(prices, w)

        emas: dict[str, list[Optional[Decimal]]] = {}
        for w in (ema_windows or [12, 26]):
            emas[f"ema_{w}"] = calculate_ema(prices, w)

        rsi_series = calculate_rsi(prices, 14) if include_rsi else None
        macd_result = calculate_macd(prices, 12, 26, 9, timestamps=timestamps) if include_macd else None
        bb_result = calculate_bollinger_bands(prices, 20, Decimal("2.0"), timestamps=timestamps) if include_bollinger else None
        atr_result = (
            calculate_atr(highs, lows, prices, period=atr_period, timestamps=timestamps)
            if include_atr
            else None
        )

        return {
            "symbol": symbol.strip().upper(),
            "timestamps": timestamps,
            "prices": prices,
            "smas": smas,
            "emas": emas,
            "rsi": rsi_series,
            "macd": macd_result,
            "bollinger": bb_result,
            "atr": atr_result,
        }

    async def get_market_intelligence(
        self,
        symbol: str,
        interval: str = "1d",
        lookback_days: int = 365,
        annualize_factor: int = 252,
    ) -> MarketIntelligenceSummary:
        """Synthesize explainable market intelligence report for a symbol."""
        prices, timestamps = await self.get_price_series(symbol, interval, lookback_days)
        return synthesize_market_intelligence(
            symbol=symbol,
            prices=prices,
            timestamps=timestamps,
            annualize_factor=annualize_factor,
        )
