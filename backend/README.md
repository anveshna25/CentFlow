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

## Current Status

The backend currently contains only the initial FastAPI foundation.

Application-specific APIs, business logic, database integration, and market-data services will be introduced in later phases.