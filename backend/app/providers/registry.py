from collections.abc import Callable
from typing import Optional

from app.core.config import get_settings
from app.core.errors import CentFlowException
from app.providers.base import BaseMarketDataProvider


class ProviderRegistry:
    """Registry for discovering, configuring, and instantiating market data providers."""

    _factories: dict[str, Callable[[], BaseMarketDataProvider]] = {}
    _instances: dict[str, BaseMarketDataProvider] = {}

    @classmethod
    def register(cls, name: str, factory: Callable[[], BaseMarketDataProvider]) -> None:
        """Register a provider factory under a given name."""
        cls._factories[name.lower()] = factory

    @classmethod
    def get(cls, name: Optional[str] = None) -> BaseMarketDataProvider:
        """Retrieve or instantiate a provider singleton by name."""
        target_name = (name or get_settings().market_data_provider).lower()
        if target_name in cls._instances:
            return cls._instances[target_name]

        factory = cls._factories.get(target_name)
        if not factory:
            available = list(cls._factories.keys())
            raise CentFlowException(
                message=f"Market data provider '{target_name}' is not registered. Available: {available}",
                code="PROVIDER_NOT_REGISTERED",
            )

        instance = factory()
        cls._instances[target_name] = instance
        return instance

    @classmethod
    def clear(cls) -> None:
        """Clear cached instances (useful for testing)."""
        cls._instances.clear()


def get_provider(name: Optional[str] = None) -> BaseMarketDataProvider:
    """Convenience helper to retrieve the active market data provider."""
    return ProviderRegistry.get(name)
