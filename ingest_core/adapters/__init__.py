"""
Model Adapters.

Adapters compile StructuredPrompt to model-specific prompt strings.
Each adapter reads its configuration from settings.adapters.<model_name>.
"""

from typing import TYPE_CHECKING

from ingest_core.adapters.base import BaseModelAdapter
from ingest_core.adapters.kling import KlingAdapter

if TYPE_CHECKING:
    from ingest_core.config.settings import Settings

__all__ = [
    "BaseModelAdapter",
    "KlingAdapter",
    "get_adapter",
    "ADAPTERS",
]


# Registry of available adapters
ADAPTERS: dict[str, type[BaseModelAdapter]] = {
    "kling": KlingAdapter,
}


def get_adapter(model_name: str, settings: "Settings | None" = None) -> BaseModelAdapter:
    """
    Get an adapter instance by model name.
    
    Args:
        model_name: Name of the target model (e.g., "kling", "runway")
        settings: Application settings (uses default if not provided)
        
    Returns:
        Configured adapter instance
        
    Raises:
        ValueError: If model not supported
    """
    if settings is None:
        from ingest_core.config import get_settings
        settings = get_settings()
    
    adapter_class = ADAPTERS.get(model_name.lower())
    if not adapter_class:
        available = ", ".join(ADAPTERS.keys())
        raise ValueError(f"Unknown model '{model_name}'. Available: {available}")
    
    return adapter_class(settings)
