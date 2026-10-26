import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _load_env_file(filepath: Path) -> None:
    """Lightweight .env file parser to populate os.environ without third-party dependencies."""
    if not filepath.is_file():
        return
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("\"'")
            if key not in os.environ:
                os.environ[key] = val


@dataclass(frozen=True)
class Settings:
    """Application configuration settings for CentFlow."""

    app_name: str
    app_env: str
    app_host: str
    app_port: int
    database_url: str
    market_data_provider: str = "mock"
    market_data_cache_enabled: bool = True
    quote_cache_ttl_seconds: int = 15
    history_cache_ttl_seconds: int = 300
    search_cache_ttl_seconds: int = 600
    asset_cache_ttl_seconds: int = 1800
    cache_max_capacity: int = 1000
    cache_eviction_policy: str = "lru"
    cache_stale_grace_seconds: int = 86400
    quote_staleness_threshold_seconds: int = 900
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")
    api_v1_prefix: str = "/api/v1"
    debug: bool = False


@lru_cache()
def get_settings() -> Settings:
    """Retrieve and cache application configuration settings."""
    # Check current directory and parent directory for .env
    for candidate_path in [Path(".env"), Path("../.env")]:
        if candidate_path.is_file():
            _load_env_file(candidate_path)
            break

    backend_dir = Path(__file__).resolve().parent.parent.parent
    default_db_path = (backend_dir / "centflow.db").as_posix()
    default_db_url = f"sqlite:///{default_db_path}"

    env = os.getenv("APP_ENV", "development").lower()
    cors_env = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    cors_origins = tuple(origin.strip() for origin in cors_env.split(",") if origin.strip())

    cache_enabled_env = os.getenv("MARKET_DATA_CACHE_ENABLED", "true").lower()
    cache_enabled = cache_enabled_env in ("1", "true", "yes", "on")

    return Settings(
        app_name=os.getenv("APP_NAME", "CentFlow"),
        app_env=env,
        app_host=os.getenv("APP_HOST", "127.0.0.1"),
        app_port=int(os.getenv("APP_PORT", "8000")),
        database_url=os.getenv("DATABASE_URL", default_db_url),
        market_data_provider=os.getenv("MARKET_DATA_PROVIDER", "mock").lower(),
        market_data_cache_enabled=cache_enabled,
        quote_cache_ttl_seconds=int(os.getenv("QUOTE_CACHE_TTL_SECONDS", "15")),
        history_cache_ttl_seconds=int(os.getenv("HISTORY_CACHE_TTL_SECONDS", "300")),
        search_cache_ttl_seconds=int(os.getenv("SEARCH_CACHE_TTL_SECONDS", "600")),
        asset_cache_ttl_seconds=int(os.getenv("ASSET_CACHE_TTL_SECONDS", "1800")),
        cache_max_capacity=int(os.getenv("CACHE_MAX_CAPACITY", "1000")),
        cache_eviction_policy=os.getenv("CACHE_EVICTION_POLICY", "lru").lower(),
        cache_stale_grace_seconds=int(os.getenv("CACHE_STALE_GRACE_SECONDS", "86400")),
        quote_staleness_threshold_seconds=int(os.getenv("QUOTE_STALENESS_THRESHOLD_SECONDS", "900")),
        cors_origins=cors_origins,
        api_v1_prefix=os.getenv("API_V1_PREFIX", "/api/v1"),
        debug=(env == "development"),
    )
