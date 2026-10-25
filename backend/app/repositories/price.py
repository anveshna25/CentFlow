from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.database.models.price import PriceModel
from app.providers.base import ProviderBar, ProviderQuote
from app.repositories.base import BaseRepository


def _to_utc(dt: datetime) -> datetime:
    """Normalize datetime to timezone-aware UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class PriceRepository(BaseRepository[PriceModel]):
    """Repository handling persistence operations for market price observations and OHLCV bars."""

    def __init__(self, db: Session):
        super().__init__(PriceModel, db)

    def get_latest_price(
        self,
        instrument_id: str,
        interval: Optional[str] = None,
    ) -> Optional[PriceModel]:
        """Fetch the most recent price observation for an instrument."""
        stmt = select(PriceModel).where(PriceModel.instrument_id == instrument_id)
        if interval:
            stmt = stmt.where(PriceModel.interval == interval)
        stmt = stmt.order_by(PriceModel.timestamp.desc()).limit(1)
        return self.db.scalars(stmt).first()

    def get_historical_prices(
        self,
        instrument_id: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        interval: Optional[str] = None,
    ) -> Sequence[PriceModel]:
        """Retrieve ordered historical price observations within an optional timestamp window."""
        stmt = select(PriceModel).where(PriceModel.instrument_id == instrument_id)
        if start is not None:
            start_ts = _to_utc(start)
            if interval == "1d":
                start_ts = start_ts.replace(hour=0, minute=0, second=0, microsecond=0)
            stmt = stmt.where(PriceModel.timestamp >= start_ts)
        if end is not None:
            end_ts = _to_utc(end)
            stmt = stmt.where(PriceModel.timestamp <= end_ts)
        if interval:
            stmt = stmt.where(PriceModel.interval == interval)
        stmt = stmt.order_by(PriceModel.timestamp.asc())
        return self.db.scalars(stmt).all()

    def count_for_instrument(
        self,
        instrument_id: str,
        interval: Optional[str] = None,
    ) -> int:
        """Count stored price observations for an instrument."""
        stmt = select(func.count()).select_from(PriceModel).where(PriceModel.instrument_id == instrument_id)
        if interval:
            stmt = stmt.where(PriceModel.interval == interval)
        return self.db.scalar(stmt) or 0

    def insert_quote_observation(
        self,
        instrument_id: str,
        quote: ProviderQuote,
        interval: str = "tick",
        source: Optional[str] = None,
    ) -> PriceModel:
        """Insert or update a real-time quote observation idempotently."""
        ts = _to_utc(quote.timestamp)

        stmt = (
            select(PriceModel)
            .where(
                PriceModel.instrument_id == instrument_id,
                PriceModel.interval == interval,
                PriceModel.source == source,
            )
            .order_by(PriceModel.timestamp.desc())
            .limit(10)
        )
        candidates = self.db.scalars(stmt).all()
        existing = next(
            (c for c in candidates if _to_utc(c.timestamp) == ts),
            None,
        )
        if existing:
            existing.price = quote.price
            existing.open = quote.open
            existing.high = quote.high
            existing.low = quote.low
            existing.close = quote.price
            existing.volume = quote.volume
            existing.currency = quote.currency
            return self.update(existing)

        record = PriceModel(
            instrument_id=instrument_id,
            timestamp=ts,
            price=quote.price,
            open=quote.open,
            high=quote.high,
            low=quote.low,
            close=quote.price,
            volume=quote.volume,
            currency=quote.currency,
            interval=interval,
            source=source,
        )
        return self.create(record)

    def bulk_insert_bars(
        self,
        instrument_id: str,
        bars: Sequence[ProviderBar],
        currency: str,
        interval: str = "1d",
        source: Optional[str] = None,
    ) -> int:
        """Bulk insert historical OHLCV bars idempotently, skipping existing points."""
        if not bars:
            return 0

        stmt = select(PriceModel.timestamp).where(
            PriceModel.instrument_id == instrument_id,
            PriceModel.interval == interval,
            PriceModel.source == source,
        )
        existing_timestamps = {_to_utc(ts) for ts in self.db.scalars(stmt).all()}

        new_entities = []
        for bar in bars:
            ts = _to_utc(bar.timestamp)
            if ts not in existing_timestamps:
                existing_timestamps.add(ts)
                new_entities.append(
                    PriceModel(
                        instrument_id=instrument_id,
                        timestamp=ts,
                        price=bar.close,
                        open=bar.open,
                        high=bar.high,
                        low=bar.low,
                        close=bar.close,
                        volume=bar.volume,
                        currency=currency,
                        interval=interval,
                        source=source,
                    )
                )

        if new_entities:
            self.db.add_all(new_entities)
            self.db.commit()

        return len(new_entities)
