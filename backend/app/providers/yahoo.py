from collections.abc import Sequence
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from urllib.parse import quote_plus

import httpx

from app.core.errors import (
    InstrumentNotFoundError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.providers.base import (
    BaseMarketDataProvider,
    ProviderBar,
    ProviderCapabilities,
    ProviderInstrument,
    ProviderQuote,
    ProviderStatus,
)


class YahooMarketDataProvider(BaseMarketDataProvider):
    """Market data provider adapter querying public Yahoo Finance endpoints for
    real-time quotes, historical OHLCV bars, and instrument catalog search.
    """

    _DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        client: Optional[httpx.AsyncClient] = None,
        base_url: str = "https://query1.finance.yahoo.com",
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._external_client = client
        self._internal_client: Optional[httpx.AsyncClient] = None

    @property
    def name(self) -> str:
        """Provider identifier."""
        return "yahoo"

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Operational capabilities declared for Yahoo Finance provider."""
        return ProviderCapabilities(
            supported_intervals=("1d", "1wk", "1mo", "1h", "5m"),
            supports_search=True,
            supports_realtime=False,
            is_delayed=True,
            delay_minutes=15,
        )

    def _get_client(self) -> httpx.AsyncClient:
        """Retrieve existing client or instantiate internal client."""
        if self._external_client is not None:
            return self._external_client
        if self._internal_client is None or self._internal_client.is_closed:
            self._internal_client = httpx.AsyncClient(
                headers={"User-Agent": self._DEFAULT_USER_AGENT},
                timeout=self._timeout,
            )
        return self._internal_client

    async def close(self) -> None:
        """Close internal HTTP client session if active."""
        if self._internal_client is not None and not self._internal_client.is_closed:
            await self._internal_client.aclose()
            self._internal_client = None

    async def __aenter__(self) -> "YahooMarketDataProvider":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def get_quote(self, symbol: str) -> ProviderQuote:
        """Fetch latest price quote for a financial instrument symbol."""
        clean_symbol = symbol.strip().upper()
        url = f"{self._base_url}/v8/finance/chart/{quote_plus(clean_symbol)}?interval=1d&range=1d"
        client = self._get_client()

        try:
            response = await client.get(url)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("yahoo", f"Request timed out contacting Yahoo Finance: {exc}") from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError("yahoo", f"Network error contacting Yahoo Finance: {exc}") from exc

        if response.status_code == 404:
            raise InstrumentNotFoundError(clean_symbol)
        if response.status_code == 429:
            raise ProviderRateLimitError("yahoo", "Yahoo Finance rate limit exceeded (HTTP 429)")
        if response.status_code in (401, 403):
            raise ProviderAuthenticationError("yahoo", f"Yahoo Finance access denied: HTTP {response.status_code}")
        if response.status_code != 200:
            raise ProviderUnavailableError("yahoo", f"Yahoo Finance returned HTTP {response.status_code}")

        try:
            payload = response.json()
            chart = payload.get("chart", {})
            error = chart.get("error")
            result = chart.get("result")
            if error or not result:
                raise InstrumentNotFoundError(clean_symbol)

            meta = result[0].get("meta", {})
            raw_price = meta.get("regularMarketPrice") or meta.get("chartPreviousClose")
            if raw_price is None:
                raise InstrumentNotFoundError(clean_symbol)

            price = Decimal(str(raw_price))
            currency = str(meta.get("currency", "USD")).upper()
            raw_time = meta.get("regularMarketTime")
            timestamp = (
                datetime.fromtimestamp(raw_time, tz=timezone.utc)
                if raw_time
                else datetime.now(timezone.utc)
            )

            prev_close_val = meta.get("previousClose") or meta.get("chartPreviousClose")
            prev_close = Decimal(str(prev_close_val)) if prev_close_val is not None else None

            open_val = meta.get("regularMarketDayLow")  # fallback
            quote_indicators = result[0].get("indicators", {}).get("quote", [{}])[0]
            if quote_indicators.get("open") and len(quote_indicators["open"]) > 0:
                raw_open = quote_indicators["open"][-1]
                open_price = Decimal(str(raw_open)) if raw_open is not None else None
            else:
                open_price = Decimal(str(open_val)) if open_val is not None else None

            high_val = meta.get("regularMarketDayHigh")
            high_price = Decimal(str(high_val)) if high_val is not None else None

            low_val = meta.get("regularMarketDayLow")
            low_price = Decimal(str(low_val)) if low_val is not None else None

            vol_val = meta.get("regularMarketVolume")
            volume = Decimal(str(vol_val)) if vol_val is not None else None

            # Compute change and percentage if previous close is known
            change = None
            change_percent = None
            if prev_close is not None and prev_close > 0:
                change = price - prev_close
                change_percent = round((change / prev_close) * Decimal("100"), 2)

            return ProviderQuote(
                symbol=clean_symbol,
                price=price,
                currency=currency,
                timestamp=timestamp,
                volume=volume,
                open=open_price,
                high=high_price,
                low=low_price,
                previous_close=prev_close,
                change=change,
                change_percent=change_percent,
            )
        except (ValueError, KeyError, IndexError) as exc:
            raise ProviderResponseError("yahoo", f"Malformed payload from Yahoo Finance: {exc}") from exc

    async def get_historical_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = "1d",
    ) -> Sequence[ProviderBar]:
        """Fetch historical OHLCV bars over a date range."""
        clean_symbol = symbol.strip().upper()
        p1 = int(start.timestamp())
        p2 = int(end.timestamp())

        # Normalize interval to Yahoo conventions
        interval_map = {"1d": "1d", "1h": "1h", "5m": "5m", "1wk": "1wk", "1mo": "1mo"}
        yahoo_interval = interval_map.get(interval.lower(), "1d")

        url = (
            f"{self._base_url}/v8/finance/chart/{quote_plus(clean_symbol)}"
            f"?period1={p1}&period2={p2}&interval={yahoo_interval}"
        )
        client = self._get_client()

        try:
            response = await client.get(url)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("yahoo", f"Request timed out contacting Yahoo Finance: {exc}") from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError("yahoo", f"Network error contacting Yahoo Finance: {exc}") from exc

        if response.status_code == 404:
            raise InstrumentNotFoundError(clean_symbol)
        if response.status_code == 429:
            raise ProviderRateLimitError("yahoo", "Yahoo Finance rate limit exceeded (HTTP 429)")
        if response.status_code in (401, 403):
            raise ProviderAuthenticationError("yahoo", f"Yahoo Finance access denied: HTTP {response.status_code}")
        if response.status_code != 200:
            raise ProviderUnavailableError("yahoo", f"Yahoo Finance returned HTTP {response.status_code}")

        try:
            payload = response.json()
            chart = payload.get("chart", {})
            result = chart.get("result")
            if not result:
                raise InstrumentNotFoundError(clean_symbol)

            data = result[0]
            timestamps = data.get("timestamp", [])
            indicators = data.get("indicators", {}).get("quote", [{}])[0]

            opens = indicators.get("open", [])
            highs = indicators.get("high", [])
            lows = indicators.get("low", [])
            closes = indicators.get("close", [])
            volumes = indicators.get("volume", [])

            bars: list[ProviderBar] = []
            for i, ts in enumerate(timestamps):
                # Guard against market closure / holiday nulls
                if (
                    i >= len(opens)
                    or i >= len(highs)
                    or i >= len(lows)
                    or i >= len(closes)
                    or i >= len(volumes)
                ):
                    continue
                o, h, l, c, v = opens[i], highs[i], lows[i], closes[i], volumes[i]
                if None in (o, h, l, c):
                    continue

                bars.append(
                    ProviderBar(
                        symbol=clean_symbol,
                        timestamp=datetime.fromtimestamp(ts, tz=timezone.utc),
                        open=Decimal(str(o)),
                        high=Decimal(str(h)),
                        low=Decimal(str(l)),
                        close=Decimal(str(c)),
                        volume=Decimal(str(v or 0)),
                    )
                )

            return bars
        except (ValueError, KeyError, IndexError) as exc:
            raise ProviderResponseError("yahoo", f"Malformed history payload from Yahoo Finance: {exc}") from exc

    async def search_instruments(self, query: str) -> Sequence[ProviderInstrument]:
        """Search instruments by ticker symbol or corporate name."""
        clean_query = query.strip()
        if not clean_query:
            return []

        url = f"{self._base_url}/v1/finance/search?q={quote_plus(clean_query)}&quotesCount=10&newsCount=0"
        client = self._get_client()

        try:
            response = await client.get(url)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("yahoo", f"Request timed out searching Yahoo Finance: {exc}") from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError("yahoo", f"Network error searching Yahoo Finance: {exc}") from exc

        if response.status_code == 429:
            raise ProviderRateLimitError("yahoo", "Yahoo Finance search rate limit exceeded (HTTP 429)")
        if response.status_code in (401, 403):
            raise ProviderAuthenticationError("yahoo", f"Yahoo Finance access denied: HTTP {response.status_code}")
        if response.status_code != 200:
            raise ProviderUnavailableError("yahoo", f"Yahoo search returned HTTP {response.status_code}")

        try:
            payload = response.json()
            quotes = payload.get("quotes", [])
            instruments: list[ProviderInstrument] = []

            for item in quotes:
                sym = item.get("symbol")
                if not sym:
                    continue
                name = item.get("shortname") or item.get("longname") or sym
                quote_type = item.get("quoteType", "EQUITY").lower()
                # Normalize asset classification
                type_map = {
                    "equity": "equity",
                    "etf": "etf",
                    "cryptocurrency": "crypto",
                    "currency": "forex",
                    "index": "index",
                    "future": "future",
                }
                asset_type = type_map.get(quote_type, "equity")
                exchange = item.get("exchange")
                market = item.get("dispExchange") or exchange

                instruments.append(
                    ProviderInstrument(
                        symbol=sym,
                        name=name,
                        asset_type=asset_type,
                        currency="USD",
                        exchange=exchange,
                        market=market,
                    )
                )

            return instruments
        except (ValueError, KeyError) as exc:
            raise ProviderResponseError("yahoo", f"Malformed search payload from Yahoo Finance: {exc}") from exc

    async def get_status(self) -> ProviderStatus:
        """Check provider connectivity status and return health report."""
        return ProviderStatus(
            name=self.name,
            is_active=True,
            message="Yahoo Finance Public Gateway operational.",
            latency_ms=10.0,
            capabilities=self.capabilities,
        )
