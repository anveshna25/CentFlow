from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from app.api.schemas.portfolio import (
    PortfolioCreateRequest,
    PortfolioResponse,
    PositionCreateRequest,
    PositionResponse,
)
from app.core.errors import NotFoundError, ValidationError
from app.database.models.portfolio import PortfolioModel, PositionModel
from app.repositories.instrument import InstrumentRepository
from app.repositories.portfolio import PortfolioRepository
from app.services.market_data import MarketDataService


class PortfolioService:
    """Core domain service orchestrating portfolio valuation, holdings tracking, and position lifecycle."""

    def __init__(self, db: Session, market_data_service: Optional[MarketDataService] = None):
        self.db = db
        self.portfolio_repo = PortfolioRepository(db)
        self.instrument_repo = InstrumentRepository(db)
        self.market_data_service = market_data_service or MarketDataService()

    async def _calculate_position_metrics(self, pos: PositionModel) -> PositionResponse:
        """Calculate market value, cost basis, and unrealized P&L using real-time quotes."""
        symbol = pos.instrument.symbol if pos.instrument else "UNKNOWN"
        name = pos.instrument.name if pos.instrument else symbol
        asset_type = pos.instrument.asset_type.value if hasattr(pos.instrument, "asset_type") and hasattr(pos.instrument.asset_type, "value") else (str(getattr(pos.instrument, "asset_type", "equity")))

        current_price = pos.average_price
        try:
            quote = await self.market_data_service.get_quote(symbol)
            if quote and quote.price is not None:
                current_price = Decimal(str(quote.price))
        except Exception:
            # Fallback to average entry price if quote fails (offline or non-catalog symbol)
            current_price = pos.average_price

        qty = pos.quantity
        avg_price = pos.average_price
        cost_basis = qty * avg_price
        market_value = qty * current_price
        unrealized_pnl = market_value - cost_basis
        unrealized_pnl_percent = (
            (unrealized_pnl / cost_basis * Decimal("100"))
            if cost_basis > Decimal("0")
            else Decimal("0")
        )

        return PositionResponse(
            id=pos.id,
            instrument_id=pos.instrument_id,
            symbol=symbol,
            name=name,
            asset_type=asset_type,
            quantity=qty,
            average_price=avg_price.quantize(Decimal("0.000001")),
            current_price=current_price.quantize(Decimal("0.000001")),
            cost_basis=cost_basis.quantize(Decimal("0.01")),
            market_value=market_value.quantize(Decimal("0.01")),
            unrealized_pnl=unrealized_pnl.quantize(Decimal("0.01")),
            unrealized_pnl_percent=unrealized_pnl_percent.quantize(Decimal("0.01")),
            currency=pos.currency or "USD",
            opened_at=pos.opened_at,
        )

    async def _build_portfolio_response(self, portfolio: PortfolioModel) -> PortfolioResponse:
        """Construct a full PortfolioResponse with real-time valuation aggregation."""
        pos_responses: list[PositionResponse] = []
        for pos in portfolio.positions:
            pos_response = await self._calculate_position_metrics(pos)
            pos_responses.append(pos_response)

        total_valuation = sum((p.market_value for p in pos_responses), Decimal("0"))
        total_cost_basis = sum((p.cost_basis for p in pos_responses), Decimal("0"))
        total_unrealized_pnl = total_valuation - total_cost_basis
        total_unrealized_pnl_percent = (
            (total_unrealized_pnl / total_cost_basis * Decimal("100"))
            if total_cost_basis > Decimal("0")
            else Decimal("0")
        )

        return PortfolioResponse(
            id=portfolio.id,
            name=portfolio.name,
            description=portfolio.description,
            base_currency=portfolio.base_currency or "USD",
            total_valuation=total_valuation.quantize(Decimal("0.01")),
            total_cost_basis=total_cost_basis.quantize(Decimal("0.01")),
            total_unrealized_pnl=total_unrealized_pnl.quantize(Decimal("0.01")),
            total_unrealized_pnl_percent=total_unrealized_pnl_percent.quantize(Decimal("0.01")),
            positions_count=len(pos_responses),
            positions=pos_responses,
            created_at=portfolio.created_at,
            updated_at=portfolio.updated_at,
        )

    async def list_portfolios(self, user_id: Optional[str] = None) -> list[PortfolioResponse]:
        """List all portfolios for the current user or system, with live valuations."""
        portfolios = self.portfolio_repo.list_with_positions(user_id=user_id)
        if not portfolios:
            # Seed default portfolio if empty
            default_pf = PortfolioModel(
                name="Main Multi-Asset",
                description="Default primary investment holdings and multi-asset position tracking",
                base_currency="USD",
                user_id=user_id,
            )
            self.portfolio_repo.create(default_pf)
            portfolios = [default_pf]

        results: list[PortfolioResponse] = []
        for pf in portfolios:
            results.append(await self._build_portfolio_response(pf))
        return results

    async def get_portfolio(self, portfolio_id: str) -> PortfolioResponse:
        """Fetch a portfolio by ID with live valuations and holdings."""
        portfolio = self.portfolio_repo.get_with_positions(portfolio_id)
        if not portfolio:
            raise NotFoundError("Portfolio", portfolio_id)
        return await self._build_portfolio_response(portfolio)

    async def create_portfolio(self, req: PortfolioCreateRequest, user_id: Optional[str] = None) -> PortfolioResponse:
        """Create and persist a new portfolio."""
        if not req.name.strip():
            raise ValidationError("Portfolio name cannot be blank.")

        portfolio = PortfolioModel(
            name=req.name.strip(),
            description=req.description.strip() if req.description else None,
            base_currency=req.base_currency.strip().upper(),
            user_id=user_id,
        )
        self.portfolio_repo.create(portfolio)
        return await self._build_portfolio_response(portfolio)

    async def add_position(self, portfolio_id: str, req: PositionCreateRequest) -> PortfolioResponse:
        """Add or accumulate a position in a portfolio."""
        portfolio = self.portfolio_repo.get_with_positions(portfolio_id)
        if not portfolio:
            raise NotFoundError("Portfolio", portfolio_id)

        clean_symbol = req.symbol.strip().upper()
        instrument = self.instrument_repo.get_by_symbol(clean_symbol)
        if not instrument:
            # Try to resolve or create instrument from active market provider
            try:
                provider_insts = await self.market_data_service.search_instruments(clean_symbol)
                found = next((pi for pi in provider_insts if pi.symbol.upper() == clean_symbol), None)
                if found:
                    instrument = self.instrument_repo.get_or_create_from_provider(found, default_currency=req.currency)
            except Exception:
                pass

        if not instrument:
            # If not yet in instrument catalog, create a basic instrument record
            from app.providers.base import ProviderInstrument
            basic_pi = ProviderInstrument(
                symbol=clean_symbol,
                name=clean_symbol,
                asset_type="equity",
                exchange="GLOBAL",
                currency=req.currency,
            )
            instrument = self.instrument_repo.get_or_create_from_provider(basic_pi, default_currency=req.currency)

        self.portfolio_repo.add_or_update_position(
            portfolio_id=portfolio.id,
            instrument_id=instrument.id,
            quantity=req.quantity,
            average_price=req.average_price,
            currency=req.currency.strip().upper(),
        )

        # Refresh and return updated portfolio
        refreshed = self.portfolio_repo.get_with_positions(portfolio_id)
        return await self._build_portfolio_response(refreshed)

    async def remove_position(self, portfolio_id: str, position_id: str) -> PortfolioResponse:
        """Delete an existing position from a portfolio."""
        portfolio = self.portfolio_repo.get_with_positions(portfolio_id)
        if not portfolio:
            raise NotFoundError("Portfolio", portfolio_id)

        deleted = self.portfolio_repo.delete_position(portfolio_id, position_id)
        if not deleted:
            raise NotFoundError("Position", position_id)

        refreshed = self.portfolio_repo.get_with_positions(portfolio_id)
        return await self._build_portfolio_response(refreshed)
