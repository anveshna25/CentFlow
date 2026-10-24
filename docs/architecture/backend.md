# CentFlow Backend Architecture

## 1. Overview & Architectural Principles

The CentFlow backend serves as the core intelligence, data processing, and service layer for the platform.

It is built with Python and FastAPI following a layered, modular architecture with strict separation of concerns:

```text
HTTP Request
     ↓
API Layer (`app/api/`)           Request validation, routing, HTTP response formatting
     ↓
Service Layer (`app/services/`)   Business logic, market data processing, workflow orchestration
     ↓
Domain Layer (`app/domain/`)     Core financial domain models and contracts
     ↓
Repository Layer (`app/repositories/`) Persistence abstraction and query execution
     ↓
Database / Storage
```

### Key Principles

1. **Separation of Concerns:** Route handlers do not contain business logic; business logic services do not know about HTTP requests or SQL queries; domain entities remain pure.
2. **Application Factory Pattern:** The application is instantiated via `create_app()` in `app/main.py`, enabling modular configuration, testing, and lifecycle management.
3. **Configuration Isolation:** All environment settings are managed centrally in `app/core/config.py` using typed, cached configuration.
4. **Extensibility Without Coupling:** Boundaries are designed so that future additions (database engines, market-data providers, analytics algorithms) slot into their respective layers without rippling changes through the codebase.

---

## 2. Directory Structure

```text
backend/
├── app/
│   ├── api/                   # HTTP routing and API endpoints
│   │   ├── routes/            # Route handler modules
│   │   │   ├── __init__.py
│   │   │   └── health.py      # Health check and probe endpoints
│   │   ├── __init__.py
│   │   └── router.py          # Central API router aggregating route namespaces
│   │
│   ├── core/                  # Core application infrastructure and settings
│   │   ├── __init__.py
│   │   └── config.py          # Typed settings and environment loading
│   │
│   ├── domain/                # Pure financial domain entities
│   │   ├── __init__.py
│   │   └── models.py          # Asset, Instrument, Exchange, Market, Price, etc.
│   │
│   ├── services/              # Business logic workflows and service operations
│   │   └── __init__.py        # Service boundaries (MarketDataService, AnalyticsService, etc.)
│   │
│   ├── repositories/          # Data access layer and persistence abstractions
│   │   └── __init__.py        # Repository interfaces separating domain from storage
│   │
│   ├── __init__.py
│   └── main.py                # Application factory: create_app()
│
├── main.py                    # Server entry point for uvicorn
├── requirements.txt           # Python package dependencies
└── README.md                  # Backend developer instructions
```

---

## 3. Layer Responsibilities

### 3.1 `app/core/` (Configuration & Foundation)
- Manages typed application configuration via [`Settings`](../../backend/app/core/config.py) and [`get_settings()`](../../backend/app/core/config.py).
- Loads environment variables from `.env` in local development without imposing heavy third-party dependencies.
- Configures application environment (`development`, `production`, `testing`), host, port, API prefixes, and debug flags.

### 3.2 `app/api/` (API & Routing Layer)
- Defines route handlers using FastAPI `APIRouter`.
- Handles HTTP request parsing, status codes, query parameters, and response serialization.
- Routes are organized by resource under `app/api/routes/` and aggregated in `app/api/router.py`.
- Exposes versioned endpoints (e.g., `/api/v1/...`) alongside top-level probes (`/health`).

### 3.3 `app/domain/` (Domain Layer)
- Encapsulates pure CentFlow financial concepts ([`Asset`](../../backend/app/domain/models.py), [`Instrument`](../../backend/app/domain/models.py), [`Exchange`](../../backend/app/domain/models.py), [`Market`](../../backend/app/domain/models.py), [`Price`](../../backend/app/domain/models.py), [`Watchlist`](../../backend/app/domain/models.py), [`Portfolio`](../../backend/app/domain/models.py), [`Position`](../../backend/app/domain/models.py)).
- Domain classes have zero dependency on database drivers, ORM frameworks, or HTTP transport libraries.

### 3.4 `app/services/` (Service Layer)
- Coordinates business workflows and platform operations.
- Houses future domain services:
  - `MarketDataService`: Ingestion, normalization, and retrieval of asset quotes.
  - `AnalyticsService`: Calculation of returns, moving averages, technical indicators, and market metrics.
  - `WatchlistService`: User watchlist curation and monitoring logic.
  - `PortfolioService`: Position tracking, portfolio valuations, and performance metrics.

### 3.5 `app/repositories/` (Repository Layer)
- Defines abstract interfaces and concrete persistence implementations for the data model ([`docs/data-model.md`](../data-model.md)).
- Isolates SQL execution, transaction management, and database drivers so services interact with repositories purely via typed methods.

---

## 4. Application Factory Pattern

The application is initialized via the `create_app()` factory function in [`backend/app/main.py`](../../backend/app/main.py):

```python
from fastapi import FastAPI
from app.api.router import api_router
from app.api.routes import health
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="CentFlow Market Intelligence Platform API",
        version="0.1.0",
        debug=settings.debug,
    )

    app.include_router(health.router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app
```

The outer entrypoint [`backend/main.py`](../../backend/main.py) instantiates the application instance for Uvicorn:

```python
from app.main import create_app

app = create_app()
```

---

## 5. Next Steps

With the backend architecture established:
1. **Issue #17 — Establish API conventions:** Define standard request/response envelopes, error formats, validation patterns, and pagination schemes.
2. **Issue #18 — Establish database foundation:** Implement persistence infrastructure, database connections, and repository patterns based on [`docs/data-model.md`](../data-model.md).
