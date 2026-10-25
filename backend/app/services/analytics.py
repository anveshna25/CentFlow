from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.analytics.calculations import (
    calculate_drawdowns,
    calculate_period_return,
    calculate_price_summary,
    calculate_returns,
    calculate_rolling_volatility,
    to_decimal,
)
from app.analytics.domain import (
    BollingerBandsResult,
    DrawdownMetric,
    MACDResult,
    MarketIntelligenceSummary,
    PeriodReturn,
    PriceSeriesSummary,
    VolatilityMetrics,
)
from app.analytics.indicators import (
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
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
                    prices = [to_decimal(m.close or m.value) for m in prices_models]
                    timestamps = [m.timestamp for m in prices_models]
                    return prices, timestamps

        # 2. Query market data service (provider/cache)
        bars = await self._market_data_service.get_historical_bars(
            symbol=clean_symbol,
            start=start,
            end=now,
            interval=interval,
        )

        prices = [to_decimal(b.close) for b in bars]
        timestamps = [b.timestamp for b in bars]
        return prices, timestamps

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
    ) -> dict[str, Any]:
        """Compute performance returns, drawdowns, and volatility metrics."""
        prices, timestamps = await self.get_price_series(symbol, interval, lookback_days)

        period_return = calculate_period_return(prices, timestamps)
        returns = calculate_returns(prices)
        volatility = calculate_rolling_volatility(returns, annualize_factor=annualize_factor)
        drawdown = calculate_drawdowns(prices)
        summary = calculate_price_summary(prices)

        return {
            "symbol": symbol.strip().upper(),
            "interval": interval,
            "lookback_days": lookback_days,
            "period_return": period_return,
            "volatility": volatility,
            "drawdown": drawdown,
            "summary": summary,
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
    ) -> dict[str, Any]:
        """Compute technical indicator series for a symbol."""
        prices, timestamps = await self.get_price_series(symbol, interval, lookback_days)

        smas: dict[str, list[Optional[Decimal]]] = {}
        for w in (sma_windows or [20, 50, 200]):
            smas[f"sma_{w}"] = calculate_sma(prices, w)

        emas: dict[str, list[Optional[Decimal]]] = {}
        for w in (ema_windows or [12, 26]):
            emas[f"ema_{w}"] = calculate_ema(prices, w)

        rsi_series = calculate_rsi(prices, 14) if include_rsi else None
        macd_result = calculate_macd(prices, 12, 26, 9, timestamps=timestamps) if include_macd else None
        bb_result = calculate_bollinger_bands(prices, 20, Decimal("2.0"), timestamps=timestamps) if include_bollinger else None

        return {
            "symbol": symbol.strip().upper(),
            "timestamps": timestamps,
            "prices": prices,
            "smas": smas,
            "emas": emas,
            "rsi": rsi_series,
            "macd": macd_result,
            "bollinger": bb_result,
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
