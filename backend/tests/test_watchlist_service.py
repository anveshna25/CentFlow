import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import Base
from app.repositories.instrument import InstrumentRepository
from app.repositories.watchlist import WatchlistRepository
from app.services.market_data import MarketDataService
from app.services.watchlist import WatchlistService


class TestWatchlistService(unittest.IsolatedAsyncioTestCase):
    """Test suite covering WatchlistRepository and WatchlistService."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = self.Session()

        self.watchlist_repo = WatchlistRepository(self.db)
        self.instrument_repo = InstrumentRepository(self.db)
        self.market_data_service = MarketDataService(enable_cache=False)
        self.service = WatchlistService(db=self.db, market_data_service=self.market_data_service)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    async def test_get_or_create_default_watchlist(self):
        wl = await self.service.get_or_create_default()
        self.assertIsNotNone(wl)
        self.assertEqual(wl.name, "My Watchlist")
        self.assertEqual(wl.items_count, 0)
        self.assertEqual(len(wl.items), 0)

        # Calling again should retrieve the existing one
        wl2 = await self.service.get_or_create_default()
        self.assertEqual(wl.id, wl2.id)

    async def test_create_and_list_watchlists(self):
        created = await self.service.create_watchlist(
            name="Tech Growth",
            description="Core technology companies",
        )
        self.assertIsNotNone(created.id)
        self.assertEqual(created.name, "Tech Growth")

        summaries = await self.service.list_watchlists()
        self.assertGreaterEqual(len(summaries), 1)
        tech_wl = next((s for s in summaries if s.name == "Tech Growth"), None)
        self.assertIsNotNone(tech_wl)
        self.assertEqual(tech_wl.description, "Core technology companies")

    async def test_add_and_enrich_item(self):
        wl = await self.service.get_or_create_default()

        # Add AAPL
        item_dto, was_created = await self.service.add_item(wl.id, "AAPL")
        self.assertTrue(was_created)
        self.assertIsNotNone(item_dto)
        self.assertEqual(item_dto.symbol, "AAPL")
        self.assertIsNotNone(item_dto.price)
        self.assertIsNotNone(item_dto.change)

        # Verify watchlist has 1 item
        updated_wl = await self.service.get_watchlist(wl.id)
        self.assertEqual(updated_wl.items_count, 1)
        self.assertEqual(updated_wl.items[0].symbol, "AAPL")

    async def test_duplicate_prevention(self):
        """Adding the same symbol multiple times must not create duplicate entries."""
        wl = await self.service.get_or_create_default()

        # First add
        item1, was_created1 = await self.service.add_item(wl.id, "MSFT")
        self.assertTrue(was_created1)

        # Duplicate add
        item2, was_created2 = await self.service.add_item(wl.id, "msft")
        self.assertFalse(was_created2)
        self.assertEqual(item1.id, item2.id)

        # Watchlist must only have 1 item
        updated_wl = await self.service.get_watchlist(wl.id)
        self.assertEqual(updated_wl.items_count, 1)

    async def test_remove_item(self):
        wl = await self.service.get_or_create_default()
        await self.service.add_item(wl.id, "BTC-USD")
        await self.service.add_item(wl.id, "ETH-USD")

        initial_wl = await self.service.get_watchlist(wl.id)
        self.assertEqual(initial_wl.items_count, 2)

        # Remove BTC-USD
        removed = await self.service.remove_item(wl.id, "BTC-USD")
        self.assertTrue(removed)

        after_remove = await self.service.get_watchlist(wl.id)
        self.assertEqual(after_remove.items_count, 1)
        self.assertEqual(after_remove.items[0].symbol, "ETH-USD")

        # Removing non-existent symbol returns False
        not_removed = await self.service.remove_item(wl.id, "NONEXISTENT")
        self.assertFalse(not_removed)

    async def test_delete_watchlist(self):
        created = await self.service.create_watchlist("Temporary")
        await self.service.add_item(created.id, "SPY")

        deleted = await self.service.delete_watchlist(created.id)
        self.assertTrue(deleted)

        retrieved = await self.service.get_watchlist(created.id)
        self.assertIsNone(retrieved)
