import unittest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes.watchlist import (
    add_item_to_watchlist,
    create_watchlist,
    delete_watchlist,
    get_default_watchlist,
    get_watchlist,
    list_watchlists,
    remove_item_from_watchlist,
)
from app.api.schemas.base import ResponseEnvelope
from app.api.schemas.watchlist import WatchlistAddSymbolRequest, WatchlistCreateRequest
from app.database.models import Base
from app.services.market_data import MarketDataService
from app.services.watchlist import WatchlistService


class TestWatchlistApiRoutes(unittest.IsolatedAsyncioTestCase):
    """Test suite covering watchlist API routes and response envelopes."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = self.Session()

        self.market_data_service = MarketDataService(enable_cache=False)
        self.service = WatchlistService(db=self.db, market_data_service=self.market_data_service)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    async def test_get_default_watchlist_route(self):
        envelope = await get_default_watchlist(enrich=True, service=self.service)
        self.assertIsInstance(envelope, ResponseEnvelope)
        self.assertEqual(envelope.data.name, "My Watchlist")
        self.assertEqual(envelope.data.items_count, 0)

    async def test_create_and_list_watchlists_route(self):
        req = WatchlistCreateRequest(name="Crypto Leaders", description="Major layer 1s")
        created_env = await create_watchlist(payload=req, service=self.service)
        self.assertIsInstance(created_env, ResponseEnvelope)
        self.assertEqual(created_env.data.name, "Crypto Leaders")

        list_env = await list_watchlists(service=self.service)
        self.assertIsInstance(list_env, ResponseEnvelope)
        self.assertTrue(any(w.name == "Crypto Leaders" for w in list_env.data))

    async def test_add_and_remove_item_route(self):
        default_env = await get_default_watchlist(service=self.service)
        wl_id = default_env.data.id

        # Add AAPL
        add_req = WatchlistAddSymbolRequest(symbol="AAPL")
        item_env = await add_item_to_watchlist(watchlist_id=wl_id, payload=add_req, service=self.service)
        self.assertIsInstance(item_env, ResponseEnvelope)
        self.assertEqual(item_env.data.symbol, "AAPL")
        self.assertTrue(item_env.meta["was_created"])

        # Add AAPL again (duplicate prevention)
        dup_env = await add_item_to_watchlist(watchlist_id=wl_id, payload=add_req, service=self.service)
        self.assertFalse(dup_env.meta["was_created"])

        # Get watchlist detail
        detail_env = await get_watchlist(watchlist_id=wl_id, service=self.service)
        self.assertEqual(detail_env.data.items_count, 1)

        # Remove AAPL
        rem_env = await remove_item_from_watchlist(watchlist_id=wl_id, symbol_or_id="AAPL", service=self.service)
        self.assertIsInstance(rem_env, ResponseEnvelope)
        self.assertTrue(rem_env.data["removed"])

        # Verify 0 items
        empty_env = await get_watchlist(watchlist_id=wl_id, service=self.service)
        self.assertEqual(empty_env.data.items_count, 0)

    async def test_get_nonexistent_watchlist_raises_404(self):
        with self.assertRaises(HTTPException) as ctx:
            await get_watchlist(watchlist_id="nonexistent-id", service=self.service)
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_delete_watchlist_route(self):
        req = WatchlistCreateRequest(name="To Delete")
        created = await create_watchlist(payload=req, service=self.service)
        wl_id = created.data.id

        del_env = await delete_watchlist(watchlist_id=wl_id, service=self.service)
        self.assertTrue(del_env.data["deleted"])

        with self.assertRaises(HTTPException):
            await get_watchlist(watchlist_id=wl_id, service=self.service)
