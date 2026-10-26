import asyncio
from decimal import Decimal
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.models import AssetModel, Base, ExchangeModel, InstrumentModel, MarketModel
from app.database.session import get_db
from app.domain.models import Asset, Exchange, Instrument, Market
from app.main import create_app
from app.providers.mock import MockMarketDataProvider
from app.repositories.asset import AssetRepository
from app.repositories.exchange import ExchangeRepository
from app.repositories.instrument import InstrumentRepository
from app.services.asset import AssetMasterService
from app.services.market_data import MarketDataService


class TestAssetMasterDataModel(unittest.TestCase):
    """Test suite covering Asset Master domain models, DB models, and to_domain mappings."""

    def test_domain_model_instantiation(self):
        asset = Asset(
            id="ast-1",
            name="Apple Inc.",
            asset_type="equity",
            sector="Technology",
            industry="Consumer Electronics",
            country="US",
            description="Consumer technology company",
            is_active=True,
        )
        self.assertEqual(asset.id, "ast-1")
        self.assertEqual(asset.sector, "Technology")

        exchange = Exchange(
            id="exc-1",
            name="NASDAQ Stock Market",
            code="NASDAQ",
            mic="XNAS",
            country="US",
            country_code="US",
            timezone="America/New_York",
            currency="USD",
        )
        self.assertEqual(exchange.code, "NASDAQ")
        self.assertEqual(exchange.mic, "XNAS")

        market = Market(
            id="mkt-1",
            name="US Equities",
            code="US_EQ",
            region="North America",
        )
        self.assertEqual(market.code, "US_EQ")

        instrument = Instrument(
            id="inst-1",
            symbol="AAPL",
            name="Apple Inc.",
            asset=asset,
            exchange=exchange,
            market=market,
            currency="USD",
            provider_symbol="AAPL",
            lot_size=Decimal("1.0"),
            is_active=True,
        )
        self.assertEqual(instrument.symbol, "AAPL")
        self.assertEqual(instrument.asset.name, "Apple Inc.")
        self.assertEqual(instrument.exchange.code, "NASDAQ")
        self.assertEqual(instrument.market.code, "US_EQ")
        self.assertEqual(instrument.asset_type, "equity")
        self.assertEqual(instrument.sector, "Technology")
        self.assertEqual(instrument.industry, "Consumer Electronics")
        self.assertEqual(instrument.country, "US")
        self.assertEqual(instrument.status, "active")

    def test_db_model_to_domain_mapping(self):
        asset_model = AssetModel(
            id="ast-db-1",
            name="Microsoft Corp.",
            asset_class="equity",
            sector="Technology",
            industry="Software—Infrastructure",
            description="Cloud and productivity software",
            is_active=True,
        )
        asset_domain = asset_model.to_domain()
        self.assertEqual(asset_domain.id, "ast-db-1")
        self.assertEqual(asset_domain.name, "Microsoft Corp.")
        self.assertEqual(asset_domain.asset_type, "equity")
        self.assertEqual(asset_domain.sector, "Technology")

        exchange_model = ExchangeModel(
            id="exc-db-1",
            code="NASDAQ",
            name="NASDAQ",
            mic="XNAS",
            country="US",
            currency="USD",
        )
        exc_domain = exchange_model.to_domain()
        self.assertEqual(exc_domain.code, "NASDAQ")
        self.assertEqual(exc_domain.mic, "XNAS")

        market_model = MarketModel(
            id="mkt-db-1",
            code="US",
            name="United States",
            region="Americas",
        )
        mkt_domain = market_model.to_domain()
        self.assertEqual(mkt_domain.code, "US")

        inst_model = InstrumentModel(
            id="inst-db-1",
            asset_id=asset_model.id,
            exchange_id=exchange_model.id,
            market_id=market_model.id,
            symbol="MSFT",
            ticker="MSFT",
            name="Microsoft Corp.",
            currency="USD",
            lot_size=Decimal("1.0"),
            is_active=True,
        )
        inst_model.asset = asset_model
        inst_model.exchange = exchange_model
        inst_model.market = market_model

        inst_domain = inst_model.to_domain()
        self.assertEqual(inst_domain.symbol, "MSFT")
        self.assertEqual(inst_domain.asset.name, "Microsoft Corp.")
        self.assertEqual(inst_domain.exchange.code, "NASDAQ")
        self.assertEqual(inst_domain.market.code, "US")


class TestAssetMasterServiceAndRepository(unittest.TestCase):
    """Test suite covering AssetRepository, InstrumentRepository, and AssetMasterService."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = self.Session()

        self.service = AssetMasterService(self.db)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_register_and_get_instrument(self):
        inst = self.service.register_instrument(
            symbol="AAPL",
            name="Apple Inc.",
            asset_name="Apple Inc.",
            asset_class="equity",
            exchange_code="NASDAQ",
            currency="USD",
            sector="Technology",
            industry="Consumer Electronics",
            description="Consumer electronics and software giant",
            provider_symbol="AAPL",
        )

        self.assertIsNotNone(inst)
        self.assertEqual(inst.symbol, "AAPL")
        self.assertEqual(inst.asset.sector, "Technology")
        self.assertEqual(inst.exchange.code, "NASDAQ")

        # Lookup by symbol
        retrieved = self.service.get_instrument("AAPL")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.symbol, "AAPL")
        self.assertEqual(retrieved.asset.name, "Apple Inc.")

    def test_resolve_symbol(self):
        self.service.register_instrument(
            symbol="BTC-USD",
            name="Bitcoin USD",
            asset_name="Bitcoin",
            asset_class="crypto",
            currency="USD",
            provider_symbol="BTC-USD",
        )

        # Exact match
        resolved = self.service.resolve_symbol("BTC-USD")
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.symbol, "BTC-USD")

        # Alternate slash representation
        resolved_slash = self.service.resolve_symbol("BTC/USD")
        self.assertIsNotNone(resolved_slash)
        self.assertEqual(resolved_slash.symbol, "BTC-USD")

        # Non-existent
        self.assertIsNone(self.service.resolve_symbol("UNKNOWN_SYM"))

    def test_list_assets_and_filtering(self):
        self.service.register_instrument(
            symbol="NVDA",
            name="NVIDIA Corporation",
            asset_name="NVIDIA Corporation",
            asset_class="equity",
            sector="Semiconductors",
        )
        self.service.register_instrument(
            symbol="JNJ",
            name="Johnson & Johnson",
            asset_name="Johnson & Johnson",
            asset_class="equity",
            sector="Healthcare",
        )
        self.service.register_instrument(
            symbol="ETH-USD",
            name="Ethereum USD",
            asset_name="Ethereum",
            asset_class="crypto",
        )

        # Filter by sector
        assets_semi, total_semi = self.service.list_assets(sector="Semiconductors")
        self.assertEqual(total_semi, 1)
        self.assertEqual(assets_semi[0].name, "NVIDIA Corporation")

        # Filter by asset class
        crypto_assets, total_crypto = self.service.list_assets(asset_class="crypto")
        self.assertEqual(total_crypto, 1)
        self.assertEqual(crypto_assets[0].name, "Ethereum")

        # Text query
        search_res, total_search = self.service.list_assets(query="Johnson")
        self.assertEqual(total_search, 1)
        self.assertEqual(search_res[0].name, "Johnson & Johnson")

    def test_enrich_asset_metadata(self):
        inst = self.service.register_instrument(
            symbol="TSLA",
            name="Tesla Inc.",
            asset_name="Tesla Inc.",
            asset_class="equity",
        )
        asset_id = inst.asset.id

        updated = self.service.enrich_asset_metadata(
            asset_id=asset_id,
            sector="Automotive",
            industry="Electric Vehicles",
            description="Leading electric vehicles manufacturer",
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated.sector, "Automotive")
        self.assertEqual(updated.industry, "Electric Vehicles")

        # Verify persisted
        refetched = self.service.get_asset(asset_id)
        self.assertEqual(refetched.sector, "Automotive")

    def test_summary_metrics(self):
        self.service.register_instrument(
            symbol="GOOGL",
            name="Alphabet Inc.",
            asset_name="Alphabet Inc.",
            asset_class="equity",
            sector="Technology",
        )
        self.service.register_instrument(
            symbol="XOM",
            name="Exxon Mobil",
            asset_name="Exxon Mobil",
            asset_class="equity",
            sector="Energy",
        )

        summary = self.service.get_summary()
        self.assertEqual(summary.total_assets, 2)
        self.assertEqual(summary.total_instruments, 2)
        self.assertEqual(summary.active_instruments, 2)
        self.assertIn("Technology", summary.sectors)
        self.assertIn("Energy", summary.sectors)

    def test_instrument_repo_count_instruments(self):
        repo = InstrumentRepository(self.db)
        self.assertEqual(repo.count_instruments(), 0)

        self.service.register_instrument(
            symbol="NVDA",
            name="Nvidia",
            asset_name="Nvidia",
            asset_class="equity",
        )
        self.assertEqual(repo.count_instruments(), 1)
        self.assertEqual(repo.count_instruments(active_only=True), 1)

    def test_provider_lookup_asset(self):
        provider = MockMarketDataProvider()
        service = MarketDataService(provider=provider, enable_cache=False)

        # Lookup existing instrument
        aapl = asyncio.run(service.lookup_asset("AAPL"))
        self.assertIsNotNone(aapl)
        self.assertEqual(aapl.symbol, "AAPL")
        self.assertEqual(aapl.asset_type, "equity")
        self.assertEqual(aapl.exchange, "NASDAQ")
        self.assertEqual(aapl.sector, "Technology")

        # Lookup unknown instrument
        unknown = asyncio.run(service.lookup_asset("UNKNOWN_SYM"))
        self.assertIsNone(unknown)


class TestAssetMasterApiRoutes(unittest.TestCase):
    """Test suite covering FastAPI HTTP endpoints for Asset Master."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = self.Session()

        # Seed data
        service = AssetMasterService(self.db)
        self.inst_aapl = service.register_instrument(
            symbol="AAPL",
            name="Apple Inc.",
            asset_name="Apple Inc.",
            asset_class="equity",
            exchange_code="NASDAQ",
            sector="Technology",
            industry="Consumer Electronics",
            description="Consumer tech giant",
        )
        self.inst_msft = service.register_instrument(
            symbol="MSFT",
            name="Microsoft Corp.",
            asset_name="Microsoft Corp.",
            asset_class="equity",
            exchange_code="NASDAQ",
            sector="Technology",
            industry="Software",
        )

        self.app = create_app()

        def override_get_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        self.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(self.app)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_list_assets_endpoint(self):
        response = self.client.get("/api/v1/assets")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("data", body)
        self.assertIn("pagination", body)
        self.assertEqual(len(body["data"]), 2)
        self.assertEqual(body["pagination"]["total"], 2)

    def test_filter_assets_endpoint(self):
        response = self.client.get("/api/v1/assets?query=Apple")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["data"]), 1)
        self.assertEqual(body["data"][0]["name"], "Apple Inc.")

    def test_get_summary_endpoint(self):
        response = self.client.get("/api/v1/assets/summary")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["total_assets"], 2)
        self.assertEqual(body["data"]["total_instruments"], 2)
        self.assertIn("Technology", body["data"]["sectors"])

    def test_get_sectors_and_classes_endpoints(self):
        resp_sec = self.client.get("/api/v1/assets/sectors")
        self.assertEqual(resp_sec.status_code, 200)
        self.assertIn("Technology", resp_sec.json()["data"])

        resp_cls = self.client.get("/api/v1/assets/classes")
        self.assertEqual(resp_cls.status_code, 200)
        self.assertIn("equity", resp_cls.json()["data"])

    def test_list_instruments_endpoint(self):
        response = self.client.get("/api/v1/assets/instruments")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        symbols = [i["symbol"] for i in body["data"]]
        self.assertIn("AAPL", symbols)
        self.assertIn("MSFT", symbols)

    def test_get_instrument_by_symbol_endpoint(self):
        response = self.client.get("/api/v1/assets/instruments/AAPL")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["symbol"], "AAPL")
        self.assertEqual(body["data"]["asset"]["name"], "Apple Inc.")
        self.assertEqual(body["data"]["exchange"]["code"], "NASDAQ")
        self.assertEqual(body["data"]["asset_type"], "equity")
        self.assertEqual(body["data"]["sector"], "Technology")
        self.assertEqual(body["data"]["status"], "active")

        # 404 for unknown instrument
        not_found = self.client.get("/api/v1/assets/instruments/NONEXISTENT")
        self.assertEqual(not_found.status_code, 404)
        self.assertEqual(not_found.json()["error"]["code"], "RESOURCE_NOT_FOUND")

    def test_get_asset_by_id_endpoint(self):
        asset_id = self.inst_aapl.asset.id
        response = self.client.get(f"/api/v1/assets/{asset_id}")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["asset"]["id"], asset_id)
        self.assertEqual(len(body["data"]["instruments"]), 1)
        self.assertEqual(body["data"]["instruments"][0]["symbol"], "AAPL")

        # 404 for unknown asset id
        not_found = self.client.get("/api/v1/assets/nonexistent-id")
        self.assertEqual(not_found.status_code, 404)

    def test_enrich_asset_endpoint(self):
        asset_id = self.inst_msft.asset.id
        patch_payload = {
            "sector": "Information Technology",
            "industry": "Enterprise Software",
            "description": "Global enterprise cloud and software platform",
        }
        response = self.client.patch(f"/api/v1/assets/{asset_id}", json=patch_payload)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["sector"], "Information Technology")
        self.assertEqual(body["data"]["industry"], "Enterprise Software")
