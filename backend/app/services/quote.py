import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import logging
from typing import Optional

from app.core.config import get_settings
from app.core.errors import (
    ProviderResponseError,
    StaleDataError,
    ValidationError,
)
from app.providers.base import BaseMarketDataProvider, ProviderQuote
from app.providers.cache import CachedMarketDataProvider
from app.providers.registry import get_provider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MarketQuote:
    """Canonical validated market quote domain structure with freshness and status indicators."""

    symbol: str
    price: Decimal
    currency: str
    timestamp: datetime
    volume: Optional[Decimal] = None
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    previous_close: Optional[Decimal] = None
    change: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    market_status: str = "UNKNOWN"
    is_stale: bool = False
    delay_minutes: int = 0
    data_source: str = "unknown"
    staleness_seconds: Optional[int] = None


def sanitize_symbol(symbol: str) -> str:
    """Validate and sanitize an instrument ticker symbol.

    Raises:
        ValidationError: If the symbol is empty, null, or contains invalid characters.
    """
    if symbol is None or not isinstance(symbol, str):
        raise ValidationError("Instrument ticker symbol cannot be empty.")

    clean = symbol.strip().upper()
    if not clean:
        raise ValidationError("Instrument ticker symbol cannot be blank.")

    if any(c in clean for c in " \t\r\n\x00"):
        raise ValidationError(f"Symbol '{symbol}' contains invalid whitespace characters.")

    return clean


def get_us_eastern_time(dt: datetime) -> datetime:
    """Accurately convert a UTC datetime to US Eastern Time accounting for Daylight Saving Time.

    US DST commences at 02:00 EST (07:00 UTC) on the second Sunday in March,
    and concludes at 02:00 EDT (06:00 UTC) on the first Sunday in November.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    year = dt.year
    march1 = datetime(year, 3, 1, tzinfo=timezone.utc)
    dst_start = datetime(year, 3, 8 + (6 - march1.weekday()) % 7, 7, 0, tzinfo=timezone.utc)

    nov1 = datetime(year, 11, 1, tzinfo=timezone.utc)
    dst_end = datetime(year, 11, 1 + (6 - nov1.weekday()) % 7, 6, 0, tzinfo=timezone.utc)

    is_dst = dst_start <= dt < dst_end
    offset = timedelta(hours=-4 if is_dst else -5)
    return dt.astimezone(timezone(offset))


def determine_market_status(symbol: str, reference_time: Optional[datetime] = None) -> str:
    """Determine market session state for an instrument.

    Returns:
        'OPEN' | 'CLOSED' | 'EXTENDED' | 'UNKNOWN'
    """
    clean = symbol.strip().upper()

    # Cryptocurrency markets operate continuously (24/7/365)
    if "-USD" in clean or clean in {"BTC", "ETH", "SOL", "USDT"} or "/" in clean:
        return "OPEN"

    now_utc = reference_time or datetime.now(timezone.utc)
    now_et = get_us_eastern_time(now_utc)
    weekday = now_et.weekday()  # 0=Monday, 6=Sunday

    # Weekend markets are closed
    if weekday >= 5:
        return "CLOSED"

    minutes_from_midnight = now_et.hour * 60 + now_et.minute

    # Pre-market: 04:00 to 09:30 ET (240 to 570 mins)
    # Regular trading hours: 09:30 to 16:00 ET (570 to 960 mins)
    # After-hours / Post-market: 16:00 to 20:00 ET (960 to 1200 mins)
    if 570 <= minutes_from_midnight < 960:
        return "OPEN"
    elif (240 <= minutes_from_midnight < 570) or (960 <= minutes_from_midnight < 1200):
        return "EXTENDED"
    else:
        return "CLOSED"


def calculate_staleness(
    quote_time: datetime,
    now_utc: datetime,
    threshold_seconds: int,
    market_status: str,
) -> tuple[int, bool]:
    """Calculate elapsed staleness duration and evaluate whether quote is stale."""
    if quote_time.tzinfo is None:
        quote_time = quote_time.replace(tzinfo=timezone.utc)
    else:
        quote_time = quote_time.astimezone(timezone.utc)

    staleness_seconds = max(0, int((now_utc - quote_time).total_seconds()))

    if market_status == "OPEN":
        is_stale = staleness_seconds > threshold_seconds
    else:
        # Outside regular trading hours, quotes from prior session are expected.
        # Mark as stale only if older than 4 days (345,600s) or 4x threshold.
        is_stale = staleness_seconds > max(threshold_seconds * 4, 345600)

    return staleness_seconds, is_stale


def validate_and_normalize_quote(
    raw_quote: ProviderQuote,
    provider: BaseMarketDataProvider,
    staleness_threshold: int,
    reference_time: Optional[datetime] = None,
) -> MarketQuote:
    """Validate numeric ranges, derive missing metrics, and enrich quote with status indicators."""
    # 1. Price validation
    if raw_quote.price is None or raw_quote.price <= Decimal("0"):
        raise ProviderResponseError(
            provider.name,
            f"Invalid non-positive quote price ({raw_quote.price}) received for symbol '{raw_quote.symbol}'.",
        )

    price = raw_quote.price

    # 2. OHLC consistency and sanitization
    high = raw_quote.high
    low = raw_quote.low
    if high is not None and low is not None:
        if high < low:
            high, low = low, high

    open_price = raw_quote.open
    if open_price is not None and open_price <= Decimal("0"):
        open_price = None

    volume = raw_quote.volume
    if volume is not None and volume < Decimal("0"):
        volume = Decimal("0")

    # 3. Derived change and change percent
    prev_close = raw_quote.previous_close
    change = raw_quote.change
    change_pct = raw_quote.change_percent

    if change is None and prev_close is not None:
        change = price - prev_close

    if change_pct is None and prev_close is not None and prev_close > Decimal("0"):
        if change is not None:
            change_pct = (change / prev_close) * Decimal("100")

    if prev_close is None and change is not None:
        prev_close = price - change

    # 4. Freshness and market status indicators
    now_utc = reference_time or datetime.now(timezone.utc)
    ts = raw_quote.timestamp
    market_status = determine_market_status(raw_quote.symbol, now_utc)
    staleness_seconds, is_stale = calculate_staleness(
        quote_time=ts,
        now_utc=now_utc,
        threshold_seconds=staleness_threshold,
        market_status=market_status,
    )

    return MarketQuote(
        symbol=raw_quote.symbol,
        price=price,
        currency=raw_quote.currency,
        timestamp=ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc),
        volume=volume,
        open=open_price,
        high=high,
        low=low,
        previous_close=prev_close,
        change=change,
        change_percent=change_pct,
        market_status=market_status,
        is_stale=is_stale,
        delay_minutes=provider.capabilities.delay_minutes,
        data_source=provider.name,
        staleness_seconds=staleness_seconds,
    )


class QuoteService:
    """Dedicated application service for retrieving, validating, and enriching
    market quote information decoupled from specific provider implementations.
    """

    def __init__(
        self,
        provider: Optional[BaseMarketDataProvider] = None,
        enable_cache: Optional[bool] = None,
        staleness_threshold_seconds: Optional[int] = None,
    ) -> None:
        raw_provider = provider or get_provider()
        settings = get_settings()
        should_cache = enable_cache if enable_cache is not None else settings.market_data_cache_enabled

        if should_cache and not isinstance(raw_provider, CachedMarketDataProvider):
            self._provider = CachedMarketDataProvider(
                provider=raw_provider,
                quote_ttl=settings.quote_cache_ttl_seconds,
                history_ttl=settings.history_cache_ttl_seconds,
                search_ttl=settings.search_cache_ttl_seconds,
                enabled=True,
            )
        else:
            self._provider = raw_provider

        self._staleness_threshold = (
            staleness_threshold_seconds
            if staleness_threshold_seconds is not None
            else settings.quote_staleness_threshold_seconds
        )

    @property
    def provider(self) -> BaseMarketDataProvider:
        """The active market data provider instance."""
        return self._provider

    @property
    def staleness_threshold_seconds(self) -> int:
        """Configured freshness threshold in seconds."""
        return self._staleness_threshold

    async def get_quote(
        self,
        symbol: str,
        max_staleness_seconds: Optional[int] = None,
    ) -> MarketQuote:
        """Fetch, validate, and enrich the latest market quote for an instrument symbol.

        Raises:
            ValidationError: If symbol is blank or invalid.
            InstrumentNotFoundError: If symbol is unrecognized.
            StaleDataError: If quote staleness exceeds max_staleness_seconds.
            ProviderError: If underlying provider encounters an error.
        """
        clean_symbol = sanitize_symbol(symbol)
        raw_quote = await self._provider.get_quote(clean_symbol)
        validated_quote = validate_and_normalize_quote(
            raw_quote=raw_quote,
            provider=self._provider,
            staleness_threshold=self._staleness_threshold,
        )

        threshold = max_staleness_seconds if max_staleness_seconds is not None else None
        if threshold is not None and validated_quote.staleness_seconds is not None:
            if validated_quote.staleness_seconds > threshold:
                raise StaleDataError(
                    symbol=clean_symbol,
                    staleness_seconds=validated_quote.staleness_seconds,
                    threshold_seconds=threshold,
                )

        return validated_quote

    async def get_quotes(
        self,
        symbols: Sequence[str],
        allow_partial: bool = True,
        max_staleness_seconds: Optional[int] = None,
    ) -> list[MarketQuote]:
        """Fetch and validate market quotes for multiple symbols concurrently.

        Args:
            symbols: Collection of instrument ticker symbols.
            allow_partial: If True, failures on individual symbols are logged and omitted;
                           if False, the first encountered error will be raised.
            max_staleness_seconds: Optional strict freshness threshold.

        Returns:
            List of successfully retrieved and validated MarketQuote records.
        """
        if not symbols:
            return []

        # Deduplicate while preserving order and validating syntax
        clean_symbols: list[str] = []
        seen: set[str] = set()
        for raw in symbols:
            try:
                cleaned = sanitize_symbol(raw)
                if cleaned not in seen:
                    seen.add(cleaned)
                    clean_symbols.append(cleaned)
            except ValidationError:
                if not allow_partial:
                    raise

        if not clean_symbols:
            return []

        tasks = [
            self.get_quote(sym, max_staleness_seconds=max_staleness_seconds)
            for sym in clean_symbols
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        quotes: list[MarketQuote] = []
        for sym, res in zip(clean_symbols, results):
            if isinstance(res, Exception):
                logger.warning("Failed to fetch quote for symbol '%s': %s", sym, res)
                if not allow_partial:
                    raise res
            else:
                quotes.append(res)

        return quotes
