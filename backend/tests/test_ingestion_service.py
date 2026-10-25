from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes.market_data import (
    backfill_historical_data,
    get_persisted_history,
    ingest_quote,
    sync_catalog,
)
from app.api.schemas.base import ResponseEnvelope
from app.api.schemas.market_data import BackfillRequestSchema, SyncCatalogRequestSchema
from app.core.errors import InstrumentNotFoundError
from app.database.models import Base
from app.providers.base import ProviderBar, ProviderInstrument, ProviderQuote
from app.repositories.asset import AssetRepository
from app.repositories.exchange import ExchangeRepository
from app.repositories.instrument import InstrumentRepository
from app.repositories.price import PriceRepository
from app.services.ingestion import MarketDataIngestionService
from app.services.market_data import MarketDataService


class TestMarketDataPersistenceAndIngestion(unittest.IsolatedAsyncioTestCase):
    """Test suite covering repositories, MarketDataIngestionService, and ingestion endpoints."""

    def setUp(self):
        # Create an isolated in-memory SQLite database
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = self.Session()

        # Repositories and Services
        self.asset_repo = AssetRepository(self.db)
        self.exchange_repo = ExchangeRepository(self.db)
        self.instrument_repo = InstrumentRepository(self.db)
        self.price_repo = PriceRepository(self.db)

        self.market_data_service = MarketDataService(enable_cache=False)
        self.ingestion_service = MarketDataIngestionService(
            db=self.db,
            market_data_service=self.market_data_service,
        )

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_asset_and_exchange_repository_get_or_create(self):
        asset = self.asset_repo.get_or_create(name="Apple Inc", asset_class="equity")
        self.assertIsNotNone(asset.id)
        self.assertEqual(asset.name, "Apple Inc")

        # Second call returns existing
        asset_duplicate = self.asset_repo.get_or_create(name="apple inc", asset_class="EQUITY")
        self.assertEqual(asset.id, asset_duplicate.id)

        exchange = self.exchange_repo.get_or_create(code="NASDAQ", name="Nasdaq Global Market")
        self.assertIsNotNone(exchange.id)
        self.assertEqual(exchange.code, "NASDAQ")

        exchange_dup = self.exchange_repo.get_or_create(code="nasdaq")
        self.assertEqual(exchange.id, exchange_dup.id)

    def test_instrument_repository_upsert_and_search(self):
        provider_inst = ProviderInstrument(
            symbol="AAPL",
            name="Apple Inc.",
            asset_type="equity",
            currency="USD",
            exchange="NASDAQ",
        )
        instrument = self.instrument_repo.get_or_create_from_provider(provider_inst)
        self.assertIsNotNone(instrument.id)
        self.assertEqual(instrument.symbol, "AAPL")
        self.assertEqual(instrument.currency, "USD")
        self.assertEqual(instrument.exchange.code, "NASDAQ")
        self.assertEqual(instrument.asset.name, "Apple Inc.")

        # Re-upsert updates name if altered and does not duplicate
        updated_provider_inst = ProviderInstrument(
            symbol="AAPL",
            name="Apple Inc. (Updated)",
            asset_type="equity",
            currency="USD",
            exchange="NASDAQ",
        )
        updated_inst = self.instrument_repo.get_or_create_from_provider(updated_provider_inst)
        self.assertEqual(updated_inst.id, instrument.id)
        self.assertEqual(updated_inst.name, "Apple Inc. (Updated)")

        # Search
        results = self.instrument_repo.search("appl")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].symbol, "AAPL")

    def test_price_repository_quote_idempotency(self):
        provider_inst = ProviderInstrument(
            symbol="NVDA",
            name="NVIDIA Corporation",
            asset_type="equity",
            currency="USD",
        )
        instrument = self.instrument_repo.get_or_create_from_provider(provider_inst)
        fixed_time = datetime(2026, 10, 24, 15, 30, tzinfo=timezone.utc)

        quote = ProviderQuote(
            symbol="NVDA",
            price=Decimal("120.50"),
            currency="USD",
            timestamp=fixed_time,
            volume=Decimal("100000"),
            open=Decimal("118.00"),
            high=Decimal("121.00"),
            low=Decimal("117.50"),
        )
        price_record = self.price_repo.insert_quote_observation(
            instrument_id=instrument.id,
            quote=quote,
            interval="tick",
            source="mock",
        )
        self.assertIsNotNone(price_record.id)
        self.assertEqual(price_record.price, Decimal("120.50"))

        # Re-inserting with updated price updates same record
        updated_quote = ProviderQuote(
            symbol="NVDA",
            price=Decimal("121.75"),
            currency="USD",
            timestamp=fixed_time,
            volume=Decimal("105000"),
        )
        price_updated = self.price_repo.insert_quote_observation(
            instrument_id=instrument.id,
            quote=updated_quote,
            interval="tick",
            source="mock",
        )
        self.assertEqual(price_updated.id, price_record.id)
        self.assertEqual(price_updated.price, Decimal("121.75"))
        self.assertEqual(self.price_repo.count_for_instrument(instrument.id), 1)

    def test_price_repository_bulk_bars_and_deduplication(self):
        provider_inst = ProviderInstrument(
            symbol="MSFT",
            name="Microsoft Corp",
            asset_type="equity",
            currency="USD",
        )
        instrument = self.instrument_repo.get_or_create_from_provider(provider_inst)

        base_time = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
        bars = [
            ProviderBar(
                symbol="MSFT",
                timestamp=base_time + timedelta(days=i),
                open=Decimal("400") + Decimal(i),
                high=Decimal("405") + Decimal(i),
                low=Decimal("398") + Decimal(i),
                close=Decimal("402") + Decimal(i),
                volume=Decimal("5000000"),
            )
            for i in range(5)
        ]

        # Initial bulk insert
        inserted = self.price_repo.bulk_insert_bars(
            instrument_id=instrument.id,
            bars=bars,
            currency="USD",
            interval="1d",
            source="mock",
        )
        self.assertEqual(inserted, 5)
        self.assertEqual(self.price_repo.count_for_instrument(instrument.id, interval="1d"), 5)

        # Re-running with same bars should insert 0 new bars
        re_inserted = self.price_repo.bulk_insert_bars(
            instrument_id=instrument.id,
            bars=bars,
            currency="USD",
            interval="1d",
            source="mock",
        )
        self.assertEqual(re_inserted, 0)
        self.assertEqual(self.price_repo.count_for_instrument(instrument.id, interval="1d"), 5)

        # Historical retrieval sorted ascending
        history = self.price_repo.get_historical_prices(
            instrument_id=instrument.id,
            start=base_time,
            end=base_time + timedelta(days=10),
            interval="1d",
        )
        self.assertEqual(len(history), 5)
        self.assertEqual(history[0].timestamp, base_time)
        self.assertEqual(history[-1].timestamp, base_time + timedelta(days=4))

        # Test latest price query
        latest = self.price_repo.get_latest_price(instrument.id, interval="1d")
        self.assertIsNotNone(latest)
        self.assertEqual(latest.timestamp, base_time + timedelta(days=4))

    async def test_ingestion_service_ingest_quote(self):
        price_record = await self.ingestion_service.ingest_quote("AAPL")
        self.assertIsNotNone(price_record.id)
        self.assertEqual(price_record.currency, "USD")
        self.assertEqual(price_record.interval, "tick")
        self.assertEqual(price_record.source, "mock")

        # Instrument should now exist in database
        inst = self.instrument_repo.get_by_symbol("AAPL")
        self.assertIsNotNone(inst)
        self.assertEqual(inst.symbol, "AAPL")

    async def test_ingestion_service_backfill_historical_bars(self):
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=7)

        summary = await self.ingestion_service.backfill_historical_bars(
            symbol="BTC-USD",
            start=start,
            end=end,
            interval="1d",
        )
        self.assertEqual(summary["symbol"], "BTC-USD")
        self.assertGreaterEqual(summary["bars_ingested"], 7)

        # Query persisted history
        history = self.ingestion_service.get_persisted_history(
            symbol="BTC-USD",
            start=start,
            end=end,
            interval="1d",
        )
        self.assertEqual(len(history), summary["bars_ingested"])

        # Second backfill over same window should ingest 0 duplicates
        summary2 = await self.ingestion_service.backfill_historical_bars(
            symbol="BTC-USD",
            start=start,
            end=end,
            interval="1d",
        )
        self.assertEqual(summary2["bars_ingested"], 0)

    async def test_ingestion_service_sync_catalog(self):
        synced = await self.ingestion_service.sync_catalog("Bitcoin")
        self.assertGreaterEqual(len(synced), 1)
        self.assertTrue(any(i.symbol == "BTC-USD" for i in synced))

        # Check DB
        in_db = self.instrument_repo.get_by_symbol("BTC-USD")
        self.assertIsNotNone(in_db)

    async def test_ensure_instrument_unknown_symbol_raises_error(self):
        with self.assertRaises(InstrumentNotFoundError):
            await self.ingestion_service.ensure_instrument("UNKNOWN_TICKER_XYZ")

    async def test_api_ingest_quote_endpoint(self):
        envelope = await ingest_quote(symbol="GOOGL", interval="tick", service=self.ingestion_service)
        self.assertIsInstance(envelope, ResponseEnvelope)
        self.assertEqual(envelope.meta["symbol"], "GOOGL")
        self.assertTrue(envelope.meta["persisted"])
        self.assertGreater(envelope.data.price, Decimal("0"))

    async def test_api_backfill_and_persisted_history_endpoints(self):
        req = BackfillRequestSchema(days=10, interval="1d")
        envelope = await backfill_historical_data(
            symbol="MSFT",
            payload=req,
            service=self.ingestion_service,
        )
        self.assertIsInstance(envelope, ResponseEnvelope)
        self.assertEqual(envelope.data.symbol, "MSFT")
        self.assertGreaterEqual(envelope.data.bars_ingested, 10)

        # Retrieve via GET persisted history route
        history_envelope = get_persisted_history(
            symbol="MSFT",
            days=15,
            interval="1d",
            service=self.ingestion_service,
        )
        self.assertIsInstance(history_envelope, ResponseEnvelope)
        self.assertEqual(history_envelope.meta["symbol"], "MSFT")
        self.assertEqual(len(history_envelope.data), envelope.data.bars_ingested)

    async def test_api_sync_catalog_endpoint(self):
        payload = SyncCatalogRequestSchema(query="Apple")
        envelope = await sync_catalog(payload=payload, service=self.ingestion_service)
        self.assertIsInstance(envelope, ResponseEnvelope)
        self.assertGreaterEqual(envelope.data.synced_count, 1)
        self.assertTrue(any(item.symbol == "AAPL" for item in envelope.data.instruments))


if __name__ == "__main__":
    unittest.main()
