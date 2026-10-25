from fastapi import APIRouter
from app.api.routes import analytics, health, market_data, watchlist

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(market_data.router)
api_router.include_router(analytics.router)
api_router.include_router(watchlist.router)
