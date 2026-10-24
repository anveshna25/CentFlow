# Frontend-Backend Integration & Communication Architecture

## 1. Overview

The integration layer in CentFlow defines how the React single-page frontend communicates with the FastAPI asynchronous backend service. It bridges client-side user experience with server-side business logic, persistence, and external market-data provider abstractions while enforcing strict security, type envelopes, error propagation, and local developer ergonomics.

```text
┌────────────────────────────────────────────────────────┐
│               Frontend (React / Vite)                 │
│                                                        │
│  [ DashboardPage / MarketsPage ]                       │
│           │                                            │
│           ▼                                            │
│  [ frontend/src/api/marketData.js ] (Service Layer)    │
│           │                                            │
│           ▼                                            │
│  [ frontend/src/api/client.js ] (apiClient / Envelope) │
└───────────────────────────┬────────────────────────────┘
                            │
              HTTP / JSON   │ (Dev: Vite Reverse Proxy)
                            ▼ (Prod: Direct CORS API)
┌────────────────────────────────────────────────────────┐
│               Backend (FastAPI / ASGI)                │
│                                                        │
│  [ CORSMiddleware (backend/app/main.py) ]             │
│           │                                            │
│           ▼                                            │
│  [ APIRouter (backend/app/api/routes/market_data.py) ] │
│           │                                            │
│           ▼                                            │
│  [ MarketDataService -> ProviderRegistry ]             │
│           │                                            │
│           ▼                                            │
│  [ ResponseEnvelope[T] / ErrorResponse ]               │
└────────────────────────────────────────────────────────┘
```

---

## 2. Communication Protocols & Proxy Architecture

### Local Development Reverse Proxy (Vite)
During development, the Vite dev server runs at `http://localhost:5173` while FastAPI runs at `http://127.0.0.1:8000`. To prevent CORS issues, avoid hardcoded backend hostnames, and streamline cookie/auth header passing:

- Vite is configured in `frontend/vite.config.js` with proxy rules:
  ```javascript
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  }
  ```
- Client calls make relative requests to `/api/v1/...` and `/health`, allowing Vite to seamlessly route traffic to the local FastAPI daemon.

### Cross-Origin Resource Sharing (CORS)
For production deployments, container environments, and remote frontends, the backend enforces configurable CORS policy:

- Configured in `backend/app/core/config.py` via `cors_origins`:
  ```python
  cors_origins: list[str] = [
      "http://localhost:5173",
      "http://127.0.0.1:5173",
      "http://localhost:3000",
      "http://127.0.0.1:3000",
  ]
  ```
- Injected in `backend/app/main.py` using FastAPI `CORSMiddleware` supporting credentials, standard HTTP methods (`GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`), and request headers.

---

## 3. Unified API Client & Contract Enforcement

### Frontend HTTP Client (`frontend/src/api/client.js`)
All outgoing HTTP requests utilize a centralized wrapper around the native browser `fetch` API:

1. **Automatic Base URL Resolution:** Defaults to `/` relative path in development (leveraging the Vite proxy) or reads `VITE_API_BASE_URL` from Vite environment variables.
2. **Content-Type & JSON Parsing:** Injects `Content-Type: application/json` and automatically serializes/deserializes request and response bodies.
3. **Envelope Unwrapping & Error Mapping:**
   - Detects HTTP status error codes (e.g., 400, 404, 500).
   - Extracts structured server error messages from `ErrorResponse` envelopes (`res.error.message` or `res.detail`).
   - Normalizes errors into clean JavaScript `Error` instances containing `.status`, `.code`, and `.details` for consumption by UI error boundaries.

### Endpoint Registry (`frontend/src/api/endpoints.js`)
Endpoint paths are strictly centralized to avoid ad-hoc string concatenation across UI components:

```javascript
export const ENDPOINTS = {
  HEALTH: '/health',
  DOCS: '/docs',
  MARKET_DATA_STATUS: '/api/v1/market-data/status',
  MARKET_DATA_QUOTE: (symbol) => `/api/v1/market-data/quotes/${encodeURIComponent(symbol)}`,
  MARKET_DATA_HISTORY: (symbol, days = 30, interval = '1d') =>
    `/api/v1/market-data/history/${encodeURIComponent(symbol)}?days=${days}&interval=${interval}`,
  MARKET_DATA_INSTRUMENTS: (query = '') =>
    query ? `/api/v1/market-data/instruments?q=${encodeURIComponent(query)}` : '/api/v1/market-data/instruments',
}
```

---

## 4. API Endpoints & Schemas

### Route Registration
Market data endpoints are mounted under `/api/v1/market-data` in `backend/app/api/router.py`:

| Method | Endpoint | Description | Response Schema |
|---|---|---|---|
| `GET` | `/health` | System health and environment ping | `HealthResponse` |
| `GET` | `/api/v1/market-data/status` | Active provider connectivity & operational status | `ResponseEnvelope[ProviderStatusSchema]` |
| `GET` | `/api/v1/market-data/quotes/{symbol}` | Normalized quote with 24h metrics for an instrument | `ResponseEnvelope[QuoteResponseSchema]` |
| `GET` | `/api/v1/market-data/history/{symbol}` | Historical OHLCV bars over a day window | `ResponseEnvelope[list[BarResponseSchema]]` |
| `GET` | `/api/v1/market-data/instruments` | Catalog search and filtering by query string | `ResponseEnvelope[list[InstrumentResponseSchema]]` |

### Response Envelopes
In accordance with CentFlow API Conventions (`docs/api-conventions.md`), every successful response is wrapped in `ResponseEnvelope[T]`:
```json
{
  "data": {
    "symbol": "AAPL",
    "price": "185.50",
    "currency": "USD",
    "timestamp": "2026-10-24T18:00:00Z",
    "volume": "52400000",
    "change": "1.60",
    "change_percent": "0.87"
  },
  "meta": {
    "source": "mock"
  }
}
```

---

## 5. Frontend Service Layer & State Lifecycle

### Service Abstraction (`frontend/src/api/marketData.js`)
Components do not call `fetch` directly; they consume async service routines:
- `getSystemHealth()`
- `getProviderStatus()`
- `getQuote(symbol)`
- `getHistoricalBars(symbol, days, interval)`
- `searchInstruments(query)`

### UI State Lifecycle & Resiliency
1. **Asynchronous Initial Fetch:** Pages like `DashboardPage` and `MarketsPage` trigger requests inside `useEffect` with cleanup cancellation tokens (`isCancelled` flag) to prevent memory leaks and race conditions.
2. **Loading States:** UI triggers the centralized `LoadingSpinner` component during active background synchronization.
3. **Graceful Fallbacks & Offline Capability:** When backend services are not running or return network errors, pages maintain deterministic defaults (`DEFAULT_BENCHMARKS`, `DEFAULT_INSTRUMENTS`) so the application remains operable.
4. **Error Presentation:** Real-time error messages and network issues display via `ErrorBanner` with an interactive "Retry" trigger.

---

## 6. Verification and Testing

1. **Backend Route Unit Tests (`backend/tests/test_api_market_data.py`):**
   - Direct asynchronous route handler execution with mock dependency injection.
   - Verifies envelope wrapping, status payloads, quotes, history bars, and instrument catalog search.
2. **Frontend Linter & Type Compliance (`npm run lint`):**
   - Enforces React Hooks rules (`react-hooks/set-state-in-effect`, `react-hooks/rules-of-hooks`).
   - Ensures zero undeclared variables and zero unused parameters.
3. **Frontend Production Compilation (`npm run build`):**
   - Validates Vite module tree bundling and static asset emission.
