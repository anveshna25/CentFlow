from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.routes.market_data import get_market_data_service
from app.api.schemas.base import ResponseEnvelope
from app.api.schemas.watchlist import (
    WatchlistAddSymbolRequest,
    WatchlistCreateRequest,
    WatchlistItemResponseSchema,
    WatchlistResponseSchema,
    WatchlistSummaryResponseSchema,
)
from app.database.session import get_db
from app.services.market_data import MarketDataService
from app.services.watchlist import WatchlistService

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


def get_watchlist_service(
    db: Session = Depends(get_db),
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> WatchlistService:
    """Dependency injector for WatchlistService."""
    return WatchlistService(db=db, market_data_service=market_data_service)


def _resolve_val(val: Any, default: Any = None) -> Any:
    """Helper to unwrap FastAPI Query default if invoked as a plain function in tests."""
    if hasattr(val, "default"):
        return val.default
    return val if val is not None else default


@router.get("", response_model=ResponseEnvelope[list[WatchlistSummaryResponseSchema]])
async def list_watchlists(
    user_id: Optional[str] = Query(default=None, description="Optional user filter."),
    service: WatchlistService = Depends(get_watchlist_service),
) -> ResponseEnvelope[list[WatchlistSummaryResponseSchema]]:
    """Retrieve catalog of all watchlists."""
    resolved_user = _resolve_val(user_id, None)
    summaries = await service.list_watchlists(user_id=resolved_user)
    return ResponseEnvelope(
        data=[
            WatchlistSummaryResponseSchema(
                id=s.id,
                name=s.name,
                description=s.description,
                items_count=s.items_count,
                symbols=s.symbols,
                created_at=s.created_at,
            )
            for s in summaries
        ]
    )


@router.get("/default", response_model=ResponseEnvelope[WatchlistResponseSchema])
async def get_default_watchlist(
    enrich: bool = Query(default=True, description="Enrich items with live market quotes."),
    service: WatchlistService = Depends(get_watchlist_service),
) -> ResponseEnvelope[WatchlistResponseSchema]:
    """Retrieve or automatically initialize the default user watchlist."""
    resolved_enrich = _resolve_val(enrich, True)
    dto = await service.get_or_create_default(enrich_quotes=resolved_enrich)
    return ResponseEnvelope(
        data=WatchlistResponseSchema(
            id=dto.id,
            name=dto.name,
            description=dto.description,
            items_count=dto.items_count,
            items=[
                WatchlistItemResponseSchema(
                    id=item.id,
                    instrument_id=item.instrument_id,
                    symbol=item.symbol,
                    name=item.name,
                    currency=item.currency,
                    exchange=item.exchange,
                    asset_type=item.asset_type,
                    added_at=item.added_at,
                    price=item.price,
                    change=item.change,
                    change_pct=item.change_pct,
                    is_up=item.is_up,
                )
                for item in dto.items
            ],
            created_at=dto.created_at,
        )
    )


@router.post("", response_model=ResponseEnvelope[WatchlistResponseSchema], status_code=status.HTTP_201_CREATED)
async def create_watchlist(
    payload: WatchlistCreateRequest,
    user_id: Optional[str] = Query(default=None, description="Optional user ID."),
    service: WatchlistService = Depends(get_watchlist_service),
) -> ResponseEnvelope[WatchlistResponseSchema]:
    """Create a new custom watchlist."""
    resolved_user = _resolve_val(user_id, None)
    dto = await service.create_watchlist(
        name=payload.name,
        description=payload.description,
        user_id=resolved_user,
    )
    return ResponseEnvelope(
        data=WatchlistResponseSchema(
            id=dto.id,
            name=dto.name,
            description=dto.description,
            items_count=0,
            items=[],
            created_at=dto.created_at,
        )
    )


@router.get("/{watchlist_id}", response_model=ResponseEnvelope[WatchlistResponseSchema])
async def get_watchlist(
    watchlist_id: str,
    enrich: bool = Query(default=True, description="Enrich items with live market quotes."),
    service: WatchlistService = Depends(get_watchlist_service),
) -> ResponseEnvelope[WatchlistResponseSchema]:
    """Retrieve a specific watchlist with its tracked asset items."""
    resolved_enrich = _resolve_val(enrich, True)
    dto = await service.get_watchlist(watchlist_id=watchlist_id, enrich_quotes=resolved_enrich)
    if not dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watchlist '{watchlist_id}' not found.",
        )

    return ResponseEnvelope(
        data=WatchlistResponseSchema(
            id=dto.id,
            name=dto.name,
            description=dto.description,
            items_count=dto.items_count,
            items=[
                WatchlistItemResponseSchema(
                    id=item.id,
                    instrument_id=item.instrument_id,
                    symbol=item.symbol,
                    name=item.name,
                    currency=item.currency,
                    exchange=item.exchange,
                    asset_type=item.asset_type,
                    added_at=item.added_at,
                    price=item.price,
                    change=item.change,
                    change_pct=item.change_pct,
                    is_up=item.is_up,
                )
                for item in dto.items
            ],
            created_at=dto.created_at,
        )
    )


@router.delete("/{watchlist_id}", response_model=ResponseEnvelope[dict[str, Any]])
async def delete_watchlist(
    watchlist_id: str,
    service: WatchlistService = Depends(get_watchlist_service),
) -> ResponseEnvelope[dict[str, Any]]:
    """Delete a watchlist."""
    deleted = await service.delete_watchlist(watchlist_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watchlist '{watchlist_id}' not found.",
        )
    return ResponseEnvelope(data={"deleted": True, "watchlist_id": watchlist_id})


@router.post("/{watchlist_id}/items", response_model=ResponseEnvelope[WatchlistItemResponseSchema], status_code=status.HTTP_200_OK)
async def add_item_to_watchlist(
    watchlist_id: str,
    payload: WatchlistAddSymbolRequest,
    service: WatchlistService = Depends(get_watchlist_service),
) -> ResponseEnvelope[WatchlistItemResponseSchema]:
    """Add an asset symbol to the watchlist with duplicate prevention."""
    item_dto, was_created = await service.add_item(
        watchlist_id=watchlist_id,
        symbol=payload.symbol,
    )
    if not item_dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watchlist '{watchlist_id}' not found or symbol could not be resolved.",
        )

    return ResponseEnvelope(
        data=WatchlistItemResponseSchema(
            id=item_dto.id,
            instrument_id=item_dto.instrument_id,
            symbol=item_dto.symbol,
            name=item_dto.name,
            currency=item_dto.currency,
            exchange=item_dto.exchange,
            asset_type=item_dto.asset_type,
            added_at=item_dto.added_at,
            price=item_dto.price,
            change=item_dto.change,
            change_pct=item_dto.change_pct,
            is_up=item_dto.is_up,
        ),
        meta={"was_created": was_created},
    )


@router.delete("/{watchlist_id}/items/{symbol_or_id}", response_model=ResponseEnvelope[dict[str, Any]])
async def remove_item_from_watchlist(
    watchlist_id: str,
    symbol_or_id: str,
    service: WatchlistService = Depends(get_watchlist_service),
) -> ResponseEnvelope[dict[str, Any]]:
    """Remove an asset from the watchlist."""
    removed = await service.remove_item(
        watchlist_id=watchlist_id,
        symbol_or_id=symbol_or_id,
    )
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item '{symbol_or_id}' not found in watchlist '{watchlist_id}'.",
        )
    return ResponseEnvelope(data={"removed": True, "symbol_or_id": symbol_or_id})
