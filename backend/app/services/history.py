"""Historical OHLCV Data Service providing standardized, validated time-series representation."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import logging
import re
from typing import Optional

from app.core.errors import InstrumentNotFoundError, ValidationError
from app.providers.base import BaseMarketDataProvider, ProviderBar
from app.providers.registry import get_provider

logger = logging.getLogger(__name__)

SUPPORTED_TIMEFRAME_RANGES: dict[str, timedelta] = {
    "1D": timedelta(days=1),
    "1W": timedelta(days=7),
    "1M": timedelta(days=30),
    "3M": timedelta(days=90),
    "6M": timedelta(days=180),
    "1Y": timedelta(days=365),
    "5Y": timedelta(days=1825),
    "ALL": timedelta(days=1825),
}

INTERVAL_NORMALIZATION: dict[str, str] = {
    "1d": "1d",
    "1D": "1d",
    "1w": "1wk",
    "1W": "1wk",
    "1wk": "1wk",
    "1WK": "1wk",
    "1m": "1mo",
    "1M": "1mo",
    "1mo": "1mo",
    "1MO": "1mo",
    "1h": "1h",
    "1H": "1h",
    "15m": "15m",
    "15M": "15m",
    "5m": "5m",
    "5M": "5m",
}

DEFAULT_INTERVAL_FOR_RANGE: dict[str, str] = {
    "1D": "1d",
    "1W": "1d",
    "1M": "1d",
    "3M": "1d",
    "6M": "1d",
    "1Y": "1d",
    "5Y": "1wk",
    "ALL": "1wk",
}


@dataclass(frozen=True)
class HistoricalSeries:
    """Standardized, validated historical OHLCV time-series representation."""

    symbol: str
    interval: str
    range: Optional[str]
    start: datetime
    end: datetime
    bars: list[ProviderBar]
    count: int
    data_source: str
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    first_close: Optional[Decimal] = None
    last_close: Optional[Decimal] = None
    period_change: Optional[Decimal] = None
    period_change_percent: Optional[Decimal] = None


def sanitize_symbol(symbol: str) -> str:
    """Validate and sanitize instrument ticker symbol."""
    if not symbol or not isinstance(symbol, str):
        raise ValidationError("Symbol parameter must be a non-empty string.")

    clean = symbol.strip().upper()
    if not clean or len(clean) > 30:
        raise ValidationError(f"Symbol length invalid: '{symbol}'. Must be between 1 and 30 characters.")

    if not re.match(r"^[A-Z0-9\.\-\/\^=_]+$", clean):
        raise ValidationError(
            f"Symbol '{symbol}' contains invalid characters. Supported symbols include alphanumeric, dot, hyphen, slash, underscore, caret."
        )

    return clean


def normalize_interval(interval: Optional[str], range_key: Optional[str] = None) -> str:
    """Validate and normalize candle aggregation interval."""
    if not interval or not interval.strip():
        if range_key and range_key in DEFAULT_INTERVAL_FOR_RANGE:
            return DEFAULT_INTERVAL_FOR_RANGE[range_key]
        return "1d"

    clean = interval.strip().lower()
    canonical = INTERVAL_NORMALIZATION.get(clean)
    if not canonical:
        supported = ", ".join(sorted(set(INTERVAL_NORMALIZATION.values())))
        raise ValidationError(
            f"Unsupported bar interval '{interval}'. Supported intervals: {supported}."
        )

    return canonical


def resolve_time_window(
    range_str: Optional[str] = None,
    days: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> tuple[datetime, datetime, Optional[str]]:
    """Resolve and validate time boundary window (start, end, normalized_range)."""
    # 1. Explicit start/end boundaries provided
    if start is not None and end is not None:
        start_utc = start if start.tzinfo else start.replace(tzinfo=timezone.utc)
        end_utc = end if end.tzinfo else end.replace(tzinfo=timezone.utc)

        if start_utc >= end_utc:
            raise ValidationError(
                f"Start datetime ({start_utc.isoformat()}) must be strictly before end datetime ({end_utc.isoformat()})."
            )

        now_utc = datetime.now(timezone.utc)
        if start_utc > now_utc + timedelta(days=1):
            raise ValidationError(
                f"Start datetime ({start_utc.isoformat()}) cannot be in the future."
            )

        range_tag = range_str.strip().upper() if range_str and range_str.strip() else None
        return start_utc, end_utc, range_tag

    # 2. Timeframe range code provided (e.g. 1D, 1W, 1M, 3M, 6M, 1Y, 5Y, ALL)
    if range_str and range_str.strip():
        clean_range = range_str.strip().upper()
        delta = SUPPORTED_TIMEFRAME_RANGES.get(clean_range)
        if not delta:
            valid_ranges = ", ".join(SUPPORTED_TIMEFRAME_RANGES.keys())
            raise ValidationError(
                f"Unsupported timeframe range '{range_str}'. Supported ranges: {valid_ranges}."
            )

        end_utc = datetime.now(timezone.utc)
        start_utc = end_utc - delta
        return start_utc, end_utc, clean_range

    # 3. Numeric days count provided
    if days is not None:
        if days < 1:
            raise ValidationError(f"Invalid days count {days}. Must be at least 1.")
        if days > 2000:
            raise ValidationError(f"Days parameter {days} exceeds maximum allowed lookback of 2000 days.")

        end_utc = datetime.now(timezone.utc)
        start_utc = end_utc - timedelta(days=days)

        # Derive matching range tag if matches standard intervals
        range_tag = None
        for r_name, r_delta in SUPPORTED_TIMEFRAME_RANGES.items():
            if r_delta == timedelta(days=days):
                range_tag = r_name
                break

        return start_utc, end_utc, range_tag

    # 4. Default fallback: 30 days (1M)
    end_utc = datetime.now(timezone.utc)
    start_utc = end_utc - timedelta(days=30)
    return start_utc, end_utc, "1M"


def validate_and_sort_bars(bars: Sequence[ProviderBar], symbol: str) -> list[ProviderBar]:
    """Validate bar integrity, ensure chronological order, and enforce zero fabrication."""
    if not bars:
        return []

    validated_bars: list[ProviderBar] = []
    seen_timestamps: set[datetime] = set()

    for bar in bars:
        # Integrity checks
        if bar.open <= 0 or bar.high <= 0 or bar.low <= 0 or bar.close <= 0:
            logger.warning("Skipping bar with non-positive price for %s at %s: O=%s, H=%s, L=%s, C=%s",
                           symbol, bar.timestamp, bar.open, bar.high, bar.low, bar.close)
            continue

        if bar.high < bar.low:
            raise ValidationError(
                f"Corrupt bar data for {symbol} at {bar.timestamp}: High ({bar.high}) is lower than Low ({bar.low})."
            )

        # Volume must be non-negative
        if bar.volume < 0:
            logger.warning("Sanitizing negative volume for %s at %s (%s -> 0)", symbol, bar.timestamp, bar.volume)
            bar = ProviderBar(
                symbol=bar.symbol,
                timestamp=bar.timestamp,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=Decimal("0"),
            )

        # Deduplicate identical timestamp observations
        if bar.timestamp in seen_timestamps:
            continue

        seen_timestamps.add(bar.timestamp)
        validated_bars.append(bar)

    # Sort strictly ascending by timestamp
    validated_bars.sort(key=lambda b: b.timestamp)

    # Note: Zero fabrication rule - missing dates/weekends/closures are authentically
    # omitted rather than artificially interpolated or synthesized with fake points.
    return validated_bars


class HistoryService:
    """Application service managing validated historical OHLCV time-series data."""

    def __init__(self, provider: Optional[BaseMarketDataProvider] = None) -> None:
        self._provider = provider or get_provider()

    @property
    def provider(self) -> BaseMarketDataProvider:
        return self._provider

    async def get_historical_series(
        self,
        symbol: str,
        range_str: Optional[str] = None,
        days: Optional[int] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        interval: Optional[str] = None,
    ) -> HistoricalSeries:
        """Retrieve, validate, and summarize historical OHLCV time-series for an instrument."""
        clean_symbol = sanitize_symbol(symbol)
        start_utc, end_utc, range_tag = resolve_time_window(
            range_str=range_str,
            days=days,
            start=start,
            end=end,
        )
        canonical_interval = normalize_interval(interval=interval, range_key=range_tag)

        # Retrieve raw bars from underlying market data provider
        try:
            raw_bars = await self._provider.get_historical_bars(
                symbol=clean_symbol,
                start=start_utc,
                end=end_utc,
                interval=canonical_interval,
            )
        except InstrumentNotFoundError:
            raise
        except Exception as exc:
            logger.error("Provider error retrieving historical bars for %s: %s", clean_symbol, exc)
            raise

        validated_bars = validate_and_sort_bars(raw_bars, clean_symbol)

        # Calculate time-series summary metrics
        min_price = None
        max_price = None
        first_close = None
        last_close = None
        period_change = None
        period_change_percent = None

        if validated_bars:
            min_price = min(b.low for b in validated_bars)
            max_price = max(b.high for b in validated_bars)
            first_close = validated_bars[0].close
            last_close = validated_bars[-1].close
            period_change = (last_close - first_close).quantize(Decimal("0.01"))
            if first_close > 0:
                period_change_percent = ((period_change / first_close) * Decimal("100")).quantize(Decimal("0.01"))
            else:
                period_change_percent = Decimal("0.00")

        return HistoricalSeries(
            symbol=clean_symbol,
            interval=canonical_interval,
            range=range_tag,
            start=start_utc,
            end=end_utc,
            bars=validated_bars,
            count=len(validated_bars),
            data_source=self._provider.name,
            min_price=min_price,
            max_price=max_price,
            first_close=first_close,
            last_close=last_close,
            period_change=period_change,
            period_change_percent=period_change_percent,
        )
