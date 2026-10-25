from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.api.schemas.base import ResponseEnvelope
from app.api.schemas.portfolio import (
    PortfolioCreateRequest,
    PortfolioResponse,
    PositionCreateRequest,
)
from app.database.session import get_db
from app.services.market_data import MarketDataService
from app.services.portfolio import PortfolioService

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


def get_market_data_service() -> MarketDataService:
    """Dependency injector for MarketDataService."""
    return MarketDataService()


def get_portfolio_service(
    db: Session = Depends(get_db),
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> PortfolioService:
    """Dependency injector for PortfolioService."""
    return PortfolioService(db=db, market_data_service=market_data_service)


@router.get("", response_model=ResponseEnvelope[list[PortfolioResponse]])
async def list_portfolios(
    service: PortfolioService = Depends(get_portfolio_service),
) -> ResponseEnvelope[list[PortfolioResponse]]:
    """List all portfolios with aggregate valuations, cost basis, and unrealized gain/loss."""
    portfolios = await service.list_portfolios()
    return ResponseEnvelope(data=portfolios)


@router.post("", response_model=ResponseEnvelope[PortfolioResponse], status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    request: PortfolioCreateRequest,
    service: PortfolioService = Depends(get_portfolio_service),
) -> ResponseEnvelope[PortfolioResponse]:
    """Create a new investment portfolio."""
    created = await service.create_portfolio(request)
    return ResponseEnvelope(data=created)


@router.get("/{portfolio_id}", response_model=ResponseEnvelope[PortfolioResponse])
async def get_portfolio(
    portfolio_id: str,
    service: PortfolioService = Depends(get_portfolio_service),
) -> ResponseEnvelope[PortfolioResponse]:
    """Retrieve detailed portfolio metrics, open positions, and valuation breakdown."""
    portfolio = await service.get_portfolio(portfolio_id)
    return ResponseEnvelope(data=portfolio)


@router.post("/{portfolio_id}/positions", response_model=ResponseEnvelope[PortfolioResponse], status_code=status.HTTP_201_CREATED)
async def add_position(
    portfolio_id: str,
    request: PositionCreateRequest,
    service: PortfolioService = Depends(get_portfolio_service),
) -> ResponseEnvelope[PortfolioResponse]:
    """Add or accumulate an asset position in a portfolio."""
    updated = await service.add_position(portfolio_id, request)
    return ResponseEnvelope(data=updated)


@router.delete("/{portfolio_id}/positions/{position_id}", response_model=ResponseEnvelope[PortfolioResponse])
async def remove_position(
    portfolio_id: str,
    position_id: str,
    service: PortfolioService = Depends(get_portfolio_service),
) -> ResponseEnvelope[PortfolioResponse]:
    """Remove a position from a portfolio and recalculate aggregate valuations."""
    updated = await service.remove_position(portfolio_id, position_id)
    return ResponseEnvelope(data=updated)
