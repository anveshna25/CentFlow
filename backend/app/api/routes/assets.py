"""API routes for canonical assets and instruments (Asset Master)."""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.schemas.asset import (
    AssetDetailResponseSchema,
    AssetEnrichRequestSchema,
    AssetMasterSummarySchema,
    AssetSchema,
    ExchangeSchema,
    InstrumentDetailSchema,
    MarketSchema,
)
from app.api.schemas.base import PaginatedResponse, PaginationMeta, ResponseEnvelope
from app.database.session import get_db
from app.domain.models import Asset, Instrument
from app.services.asset import AssetMasterService

router = APIRouter(prefix="/assets", tags=["assets"])


def get_asset_master_service(db: Session = Depends(get_db)) -> AssetMasterService:
    """Dependency injector for AssetMasterService."""
    return AssetMasterService(db=db)


def _resolve_val(val: Any, default: Any = None) -> Any:
    """Helper to unwrap FastAPI Query default if invoked as a plain function in tests."""
    if hasattr(val, "default"):
        return val.default
    return val if val is not None else default


def _to_asset_schema(asset: Asset) -> AssetSchema:
    return AssetSchema(
        id=asset.id,
        name=asset.name,
        asset_type=asset.asset_type,
        sector=asset.sector,
        industry=asset.industry,
        country=asset.country,
        description=asset.description,
        is_active=asset.is_active,
    )


def _to_instrument_schema(inst: Instrument) -> InstrumentDetailSchema:
    return InstrumentDetailSchema(
        id=inst.id,
        symbol=inst.symbol,
        name=inst.name,
        currency=inst.currency,
        provider_symbol=inst.provider_symbol,
        lot_size=float(inst.lot_size),
        is_active=inst.is_active,
        asset=_to_asset_schema(inst.asset),
        exchange=ExchangeSchema(
            id=inst.exchange.id,
            name=inst.exchange.name,
            code=inst.exchange.code,
            country=inst.exchange.country,
            country_code=inst.exchange.country_code,
            timezone=inst.exchange.timezone,
            currency=inst.exchange.currency,
            is_active=inst.exchange.is_active,
        ) if inst.exchange else None,
        market=MarketSchema(
            id=inst.market.id,
            name=inst.market.name,
            code=inst.market.code,
            region=inst.market.region,
            description=inst.market.description,
            is_active=inst.market.is_active,
        ) if inst.market else None,
    )


@router.get("", response_model=PaginatedResponse[AssetSchema])
async def list_assets(
    asset_class: Optional[str] = Query(default=None, description="Filter by asset class (e.g. equity, crypto)"),
    sector: Optional[str] = Query(default=None, description="Filter by sector"),
    query: Optional[str] = Query(default=None, description="Search term for name or description"),
    is_active: Optional[bool] = Query(default=None, description="Filter active assets"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    limit: int = Query(default=50, ge=1, le=200, description="Pagination limit"),
    service: AssetMasterService = Depends(get_asset_master_service),
) -> PaginatedResponse[AssetSchema]:
    """List canonical assets with optional filtering and pagination."""
    resolved_class = _resolve_val(asset_class, None)
    resolved_sector = _resolve_val(sector, None)
    resolved_query = _resolve_val(query, None)
    resolved_active = _resolve_val(is_active, None)
    resolved_offset = _resolve_val(offset, 0)
    resolved_limit = _resolve_val(limit, 50)

    assets, total = service.list_assets(
        asset_class=resolved_class,
        sector=resolved_sector,
        query=resolved_query,
        is_active=resolved_active,
        offset=resolved_offset,
        limit=resolved_limit,
    )

    data = [_to_asset_schema(a) for a in assets]
    return PaginatedResponse(
        data=data,
        pagination=PaginationMeta(
            limit=resolved_limit,
            offset=resolved_offset,
            total=total,
            has_next=(resolved_offset + len(data)) < total,
        ),
    )


@router.get("/summary", response_model=ResponseEnvelope[AssetMasterSummarySchema])
async def get_summary(
    service: AssetMasterService = Depends(get_asset_master_service),
) -> ResponseEnvelope[AssetMasterSummarySchema]:
    """Retrieve summary metrics and taxonomy from the Asset Master."""
    summary = service.get_summary()
    return ResponseEnvelope(
        data=AssetMasterSummarySchema(
            total_assets=summary.total_assets,
            total_instruments=summary.total_instruments,
            active_instruments=summary.active_instruments,
            sectors=summary.sectors,
            asset_classes=summary.asset_classes,
        )
    )


@router.get("/sectors", response_model=ResponseEnvelope[list[str]])
async def list_sectors(
    service: AssetMasterService = Depends(get_asset_master_service),
) -> ResponseEnvelope[list[str]]:
    """List all registered industry sectors."""
    sectors = service.asset_repo.list_sectors()
    return ResponseEnvelope(data=sectors)


@router.get("/classes", response_model=ResponseEnvelope[list[str]])
async def list_asset_classes(
    service: AssetMasterService = Depends(get_asset_master_service),
) -> ResponseEnvelope[list[str]]:
    """List all registered asset classes."""
    classes = service.asset_repo.list_asset_classes()
    return ResponseEnvelope(data=classes)


@router.get("/instruments", response_model=ResponseEnvelope[list[InstrumentDetailSchema]])
async def list_instruments(
    asset_id: Optional[str] = Query(default=None, description="Filter by parent asset ID"),
    exchange: Optional[str] = Query(default=None, description="Filter by exchange code"),
    active_only: bool = Query(default=True, description="Filter active instruments only"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    service: AssetMasterService = Depends(get_asset_master_service),
) -> ResponseEnvelope[list[InstrumentDetailSchema]]:
    """List instruments with joined asset, exchange, and market relations."""
    instruments = service.list_instruments(
        asset_id=_resolve_val(asset_id, None),
        exchange_code=_resolve_val(exchange, None),
        active_only=_resolve_val(active_only, True),
        offset=_resolve_val(offset, 0),
        limit=_resolve_val(limit, 100),
    )
    return ResponseEnvelope(data=[_to_instrument_schema(i) for i in instruments])


@router.get("/instruments/{symbol}", response_model=ResponseEnvelope[InstrumentDetailSchema])
async def get_instrument(
    symbol: str,
    service: AssetMasterService = Depends(get_asset_master_service),
) -> ResponseEnvelope[InstrumentDetailSchema]:
    """Retrieve canonical instrument details by symbol or provider symbol."""
    inst = service.resolve_symbol(symbol)
    if not inst:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instrument '{symbol}' not found in Asset Master",
        )
    return ResponseEnvelope(data=_to_instrument_schema(inst))


@router.get("/{asset_id}", response_model=ResponseEnvelope[AssetDetailResponseSchema])
async def get_asset(
    asset_id: str,
    service: AssetMasterService = Depends(get_asset_master_service),
) -> ResponseEnvelope[AssetDetailResponseSchema]:
    """Retrieve canonical asset along with its associated tradable instruments."""
    result = service.get_asset_with_instruments(asset_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_id}' not found in Asset Master",
        )
    asset, instruments = result
    return ResponseEnvelope(
        data=AssetDetailResponseSchema(
            asset=_to_asset_schema(asset),
            instruments=[_to_instrument_schema(i) for i in instruments],
        )
    )


@router.patch("/{asset_id}", response_model=ResponseEnvelope[AssetSchema])
async def enrich_asset(
    asset_id: str,
    payload: AssetEnrichRequestSchema,
    service: AssetMasterService = Depends(get_asset_master_service),
) -> ResponseEnvelope[AssetSchema]:
    """Enrich metadata (sector, industry, description) for an existing asset."""
    updated = service.enrich_asset_metadata(
        asset_id=asset_id,
        sector=payload.sector,
        industry=payload.industry,
        description=payload.description,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_id}' not found to enrich",
        )
    return ResponseEnvelope(data=_to_asset_schema(updated))
