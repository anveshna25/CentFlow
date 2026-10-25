# CentFlow Market-Data Provider Abstraction

## 1. Overview & Philosophy

The CentFlow platform requires market data (quotes, historical prices, instrument metadata) from external vendors. However, directly coupling business logic, database models, or API endpoints to a specific third-party provider (such as Yahoo Finance, Alpha Vantage, Polygon, or Twelve Data) creates severe vendor lock-in, fragile schemas, and difficult testability.

To maintain architectural integrity, CentFlow enforces an **Adapter-based Provider Abstraction** layer.

### Core Architectural Principles

1. **Vendor Decoupling:** Core domain logic and API routes never communicate with third-party market data libraries directly.
2. **Normalized Contracts:** All market data providers translate proprietary vendor responses into CentFlow's normalized Data Transfer Objects (`ProviderQuote`, `ProviderBar`, `ProviderInstrument`).
3. **Pluggable Registry:** Providers are registered dynamically with `ProviderRegistry` and instantiated via configuration (`MARKET_DATA_PROVIDER`), making local testing and provider migration seamless.
4. **Service Boundary:** `MarketDataService` serves as the single facade for upper layers to interact with market data.

---

## 2. Conceptual Architecture

```text
       ┌───────────────────────────────┐
       │   FastAPI API / Route Layer   │
       └──────────────┬────────────────┘
                      │
                      ▼
       ┌───────────────────────────────┐
       │      MarketDataService        │
       └──────────────┬────────────────┘
                      │
                      ▼
       ┌───────────────────────────────┐
       │    BaseMarketDataProvider     │  (Contract / Interface)
       └───────┬──────────────┬────────┘
               │              │
      ┌────────▼────────┐    ┌▼─────────────────────────┐
      │  MockProvider   │    │  External Vendor Adapter │
      │  (Simulated)    │    │  (Yahoo, Polygon, etc.)  │
      └─────────────────┘    └──────────────────────────┘
```

---

## 3. Directory Structure

```text
backend/app/
├── core/
│   └── cache.py              # AsyncMemoryCache with TTL & single-flight
├── providers/
│   ├── __init__.py           # Package exports & default registration
│   ├── base.py               # BaseMarketDataProvider ABC & normalized DTOs
│   ├── registry.py           # ProviderRegistry & get_provider helper
│   ├── mock.py               # Deterministic MockMarketDataProvider
│   ├── yahoo.py              # Live YahooMarketDataProvider (HTTP adapter)
│   └── cache.py              # CachedMarketDataProvider proxy decorator
│
└── services/
    ├── __init__.py           # Exports MarketDataService
    └── market_data.py        # MarketDataService application orchestrator
```

---

## 4. Normalized Data Contracts

All providers conform to standardized immutable transfer objects defined in [`backend/app/providers/base.py`](../../backend/app/providers/base.py):

### 4.1 `ProviderQuote`
Represents a point-in-time quote observation:
- `symbol: str` (e.g. `"AAPL"`)
- `price: Decimal`
- `currency: str` (e.g. `"USD"`)
- `timestamp: datetime` (UTC)
- `volume: Optional[Decimal]`
- `open: Optional[Decimal]`, `high: Optional[Decimal]`, `low: Optional[Decimal]`
- `previous_close: Optional[Decimal]`
- `change: Optional[Decimal]`, `change_percent: Optional[Decimal]`

### 4.2 `ProviderBar`
Represents an aggregated OHLCV time-series candle:
- `symbol: str`
- `timestamp: datetime`
- `open: Decimal`, `high: Decimal`, `low: Decimal`, `close: Decimal`
- `volume: Decimal`

### 4.3 `ProviderInstrument`
Represents instrument search and identification metadata:
- `symbol: str`
- `name: str`
- `asset_type: str` (e.g. `"equity"`, `"cryptocurrency"`, `"etf"`)
- `currency: Optional[str]`, `exchange: Optional[str]`, `market: Optional[str]`

### 4.4 `ProviderStatus`
Health and connectivity diagnostic:
- `name: str`
- `is_active: bool`
- `message: Optional[str]`

---

## 5. Interface Definition (`BaseMarketDataProvider`)

Defined in [`backend/app/providers/base.py`](../../backend/app/providers/base.py):

```python
class BaseMarketDataProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def get_quote(self, symbol: str) -> ProviderQuote: ...

    @abstractmethod
    async def get_historical_bars(
        self, symbol: str, start: datetime, end: datetime, interval: str = "1d"
    ) -> Sequence[ProviderBar]: ...

    @abstractmethod
    async def search_instruments(self, query: str) -> Sequence[ProviderInstrument]: ...

    @abstractmethod
    async def get_status(self) -> ProviderStatus: ...
```

---

## 6. Provider Registry & Selection

Providers are registered in [`backend/app/providers/registry.py`](../../backend/app/providers/registry.py):

```python
# Registered providers
ProviderRegistry.register("mock", MockMarketDataProvider)
ProviderRegistry.register("yahoo", YahooMarketDataProvider)

# Resolving active provider based on environment setting
provider = get_provider()
```

### Configuration (`backend/app/core/config.py`)
- `MARKET_DATA_PROVIDER`: Name of provider to instantiate (default: `"mock"`).
- In staging/production, this environment variable can be switched (e.g., `MARKET_DATA_PROVIDER=yahoo`) without modifying application code.

---

## 7. Live Adapter Implementation (`YahooMarketDataProvider`)

Defined in [`backend/app/providers/yahoo.py`](../../backend/app/providers/yahoo.py):
- **HTTP Client:** Uses `httpx.AsyncClient` with custom user agent and timeout settings. Supports external client injection for deterministic offline unit testing.
- **Quote Extraction:** Parses `chart.result[0].meta` and indicators, normalizing into `ProviderQuote` with absolute and percentage change calculations.
- **Historical Bars:** Queries epoch-based intervals (`period1`, `period2`), skipping null/holiday entries, normalizing into `ProviderBar` candles.
- **Search & Identification:** Queries Yahoo search endpoint, normalizing ticker, company name, exchange venue, and asset class (`equity`, `crypto`, `etf`, `forex`, `index`).
- **Error Mapping:** Converts HTTP 404 and empty results into `InstrumentNotFoundError`, and timeouts/5xx errors into `ProviderUnavailableError`.

---

## 8. In-Memory Caching & Rate-Limiting Layer

To prevent exceeding upstream provider rate limits and shield the platform from duplicate concurrent queries, CentFlow incorporates an asynchronous caching and single-flight request coalescing architecture:

### 8.1 `AsyncMemoryCache` ([`backend/app/core/cache.py`](../../backend/app/core/cache.py))
- **TTL Expiration:** Each cache entry maintains an absolute expiration timestamp (`now + ttl_seconds`), automatically evicted on read or via background cleanup.
- **Single-Flight Request Coalescing:** When multiple concurrent coroutines request the same uncached key simultaneously, only one leader execution triggers the remote factory call while follower tasks await the shared future.
- **Capacity Management:** High-water mark capping (`max_capacity=1000`) with automatic oldest/expired item eviction.
- **Metrics Telemetry:** Tracks `hits`, `misses`, `evictions`, and `coalesced` requests.

### 8.2 `CachedMarketDataProvider` ([`backend/app/providers/cache.py`](../../backend/app/providers/cache.py))
Transparent proxy decorator implementing `BaseMarketDataProvider`:
- **Quote Caching:** Keyed by `quote:{SYMBOL}`, default TTL: 15 seconds.
- **Historical Bars Caching:** Keyed by `history:{SYMBOL}:{START}:{END}:{INTERVAL}`, default TTL: 300 seconds (5 minutes).
- **Search Caching:** Keyed by `search:{QUERY}`, default TTL: 600 seconds (10 minutes).
- **Diagnostic Bypass:** `get_status()` bypasses cache to always report live provider connectivity.

### 8.3 Configuration (`backend/app/core/config.py`)
- `MARKET_DATA_CACHE_ENABLED`: Master toggle (default: `true`).
- `QUOTE_CACHE_TTL_SECONDS`: Quote cache TTL (default: `15`).
- `HISTORY_CACHE_TTL_SECONDS`: History bars cache TTL (default: `300`).
- `SEARCH_CACHE_TTL_SECONDS`: Search results cache TTL (default: `600`).

---

## 9. Service Layer (`MarketDataService`)

The [`MarketDataService`](../../backend/app/services/market_data.py) encapsulates business operations, automatically wrapping the active provider with `CachedMarketDataProvider` when caching is enabled:

```python
service = MarketDataService()
quote = await service.get_quote("AAPL")
history = await service.get_historical_bars("AAPL", start_date, end_date)
instruments = await service.search_instruments("Apple")
cache_stats = service.get_cache_stats()  # {"hits": 12, "misses": 3, "coalesced": 5, ...}
```

It also offers translation utilities to map normalized provider models into domain entities (e.g. `to_domain_price(quote, instrument)`).

---

## 10. Remaining Phase 3 Roadmap

Phase 3 (Market Data Engine & Ingestion) progresses through:
1. **Live Adapter:** `YahooMarketDataProvider` integrated with `ProviderRegistry` and `Settings`. (Completed)
2. **In-Memory Caching & Rate-Limiting:** Transparent TTL caching for quotes, bars, and search with single-flight request coalescing. (Completed)
3. **Data Persistence:** Ingestion service writing normalized quotes and OHLCV bars into `prices` and `instruments` tables via `PriceRepository`.
4. **Interactive Frontend Visualizations:** Time-series candlestick/line charts, interval toggles, and live search autocomplete.
