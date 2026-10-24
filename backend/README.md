# Backend

The CentFlow backend is built using Python and FastAPI.

## Development Setup

The backend uses a Python virtual environment for local development.

### Install Dependencies

From the `backend/` directory:

```bash
pip install -r requirements.txt
```

### Run the Development Server

The backend development server can be started with:

```bash
uvicorn main:app --reload
```

The backend API will be available locally through the configured development port.

FastAPI's interactive API documentation is available at:

```text
/docs
```

## Architecture

The backend follows a modular, layered architecture:
- `app/core/`: Configuration, settings, and environment loading.
- `app/api/`: Routing, request validation, and endpoint handlers.
- `app/domain/`: Pure financial domain models and definitions.
- `app/services/`: Application workflows and business logic.
- `app/repositories/`: Persistence abstraction and data access interfaces.

See [Backend Architecture](../docs/architecture/backend.md) for full architectural documentation.