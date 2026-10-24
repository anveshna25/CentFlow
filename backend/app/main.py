from fastapi import FastAPI
from app.api.router import api_router
from app.api.routes import health
from app.core.config import get_settings


def create_app() -> FastAPI:
    """Application factory for CentFlow FastAPI backend."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="CentFlow Market Intelligence Platform API",
        version="0.1.0",
        debug=settings.debug,
    )

    # Root health endpoint for direct health probes
    app.include_router(health.router)

    # Versioned API router
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app
