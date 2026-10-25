from fastapi import APIRouter
from app.api.routes import analytics, health, market_data, portfolios, watchlist

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(market_data.router)
api_router.include_router(analytics.router)
api_router.include_router(watchlist.router)
api_router.include_router(portfolios.router)

