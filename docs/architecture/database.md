# CentFlow Database Architecture & Foundation

## 1. Overview & Philosophy

The CentFlow database foundation establishes the persistence layer for the platform, translating the conceptual domain model ([`docs/domain-model.md`](../domain-model.md)) and persistence specification ([`docs/data-model.md`](../data-model.md)) into concrete database models, connection management, migrations, and repository abstractions.

### Core Architectural Principles

1. **Decoupled Persistence:** Business and service layers interact with repositories rather than raw database sessions or direct SQL statements.
2. **Dual-Environment Support:** The persistence layer supports lightweight SQLite for local development and automated testing out-of-the-box, while seamlessly connecting to PostgreSQL in production via connection strings.
3. **Migration-First Schema Evolution:** All schema modifications are tracked as version-controlled migration scripts using Alembic.
4. **Strong Typing & Auditability:** All stateful models enforce UUID surrogate keys, foreign key constraints, explicit nullability, and UTC audit timestamps.

---

## 2. Technology Stack

- **ORM & Data Access:** SQLAlchemy 2.0 (modern 2.0 `select()` syntax and declarative mappings).
- **Migration Engine:** Alembic.
- **Supported Engines:**
  - `sqlite:///...`: Local development, offline development, automated tests.
  - `postgresql+psycopg://...` / `postgresql://...`: Staging and production deployments.

---

## 3. Directory Structure

```text
backend/
├── alembic/                   # Alembic migration environment
│   ├── versions/              # Migration scripts
│   │   └── b6601f2a7d57_initial_schema.py
│   ├── env.py                 # Migration runtime configuration
│   └── script.py.mako         # Template for new migrations
├── alembic.ini                # Alembic configuration file
│
├── app/
│   ├── core/
│   │   └── config.py          # Contains database_url configuration
│   │
│   ├── database/
│   │   ├── __init__.py        # Exports Base, SessionLocal, engine, get_db
│   │   ├── session.py         # Engine creation, sessionmaker, get_db dependency
│   │   └── models/            # Declarative SQLAlchemy models
│   │       ├── __init__.py    # Aggregates and exports all models
│   │       ├── base.py        # Base, TimestampMixin, generate_uuid
│   │       ├── asset.py       # AssetModel ('assets')
│   │       ├── exchange.py    # ExchangeModel ('exchanges')
│   │       ├── market.py      # MarketModel ('markets')
│   │       ├── instrument.py  # InstrumentModel ('instruments')
│   │       ├── price.py       # PriceModel ('prices')
│   │       ├── watchlist.py   # WatchlistModel, WatchlistInstrumentModel
│   │       └── portfolio.py   # PortfolioModel, PositionModel
│   │
│   └── repositories/
│       ├── __init__.py        # Exports BaseRepository
│       └── base.py            # Generic BaseRepository[T] with CRUD operations
```

---

## 4. Connection & Session Management

### 4.1 Configuration
Database settings are managed in [`backend/app/core/config.py`](file:///c:/Users/WINNTUSIT/Desktop/CentFlow/backend/app/core/config.py):
- `DATABASE_URL`: Defaults to `sqlite:///./centflow.db` (resolved to absolute path in `backend/`).
- Staging/production environments override this via `.env` or environment variables:
  ```bash
  DATABASE_URL=postgresql://user:password@localhost:5432/centflow
  ```

### 4.2 FastAPI Session Dependency
FastAPI route handlers and service factories inject database sessions via `get_db` from [`backend/app/database/session.py`](file:///c:/Users/WINNTUSIT/Desktop/CentFlow/backend/app/database/session.py):

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db

@router.get("/example")
def example_endpoint(db: Session = Depends(get_db)):
    ...
```

---

## 5. Declarative Models Mapping

The declarative models correspond directly to the approved data model in [`docs/data-model.md`](../data-model.md):

| Table | SQLAlchemy Model | Key Relationships |
| :--- | :--- | :--- |
| `assets` | `AssetModel` | 1-to-N with `InstrumentModel` |
| `exchanges` | `ExchangeModel` | 1-to-N with `InstrumentModel` |
| `markets` | `MarketModel` | 1-to-N with `InstrumentModel` |
| `instruments` | `InstrumentModel` | Belongs to `AssetModel`, `ExchangeModel`, `MarketModel`; 1-to-N with `PriceModel`, `PositionModel`, `WatchlistInstrumentModel` |
| `prices` | `PriceModel` | Belongs to `InstrumentModel`; indexed on `(instrument_id, timestamp)` |
| `watchlists` | `WatchlistModel` | 1-to-N with `WatchlistInstrumentModel` |
| `watchlist_instruments` | `WatchlistInstrumentModel` | Many-to-Many join between `watchlists` and `instruments` |
| `portfolios` | `PortfolioModel` | 1-to-N with `PositionModel` |
| `positions` | `PositionModel` | Belongs to `PortfolioModel` and `InstrumentModel` |

---

## 6. Migration Commands (Alembic)

All migration commands should be run from the `backend/` directory:

```bash
cd backend

# Apply all pending migrations to the database
alembic upgrade head

# Generate a new migration after updating models
alembic revision --autogenerate -m "describe_changes"

# Rollback the last applied migration
alembic downgrade -1
```

---

## 7. Repository Pattern (`BaseRepository[T]`)

The generic [`BaseRepository`](file:///c:/Users/WINNTUSIT/Desktop/CentFlow/backend/app/repositories/base.py) provides standard persistence operations:
- `get_by_id(id: str) -> Optional[ModelType]`
- `list(offset: int = 0, limit: int = 20) -> Sequence[ModelType]`
- `count() -> int`
- `create(entity: ModelType) -> ModelType`
- `update(entity: ModelType) -> ModelType`
- `delete(entity: ModelType) -> None`

Domain services subclass or wrap `BaseRepository` to implement custom query workflows without exposing SQLAlchemy internals to upper layers.
