"""
Base Model Adapter.

Abstract interface for compiling StructuredPrompt to model-specific strings.
Each adapter reads its configuration from settings.py (not YAML files).
"""

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ingest_core.config.settings import Settings

from ingest_core.models.prompt_schema import StructuredPrompt


class BaseModelAdapter(ABC):
    """
    Abstract base class for model-specific prompt adapters.
    
    Each adapter knows how to compile a StructuredPrompt into
    the specific syntax that works best for its target model.
    
    Configuration is read from settings.adapters.<model_name>.
    """
    
    name: str = "base"
    
    def __init__(self, settings: "Settings"):
        """
        Initialize adapter with settings.
        
        Args:
            settings: Application settings containing adapter config
        """
        self.settings = settings
        self._config = self._get_adapter_config()
    
    @abstractmethod
    def _get_adapter_config(self) -> Any:
        """Get this adapter's config from settings."""
        pass
    
    @abstractmethod
    def compile(self, prompt: StructuredPrompt) -> str:
        """
        Compile StructuredPrompt to model-specific string.
        
        Args:
            prompt: The structured prompt to compile
            
        Returns:
            Final prompt string optimized for this model
        """
        pass
    
    @property
    def version(self) -> str:
        """Get adapter version from config."""
        return getattr(self._config, "version", "1.0")
    
    @property
    def category_order(self) -> list[str]:
        """Get the preferred order of categories for this model."""
        return getattr(self._config, "category_order", [
            "subject", "appearance", "environment", "lighting",
            "camera", "motion", "mood", "style", "technical"
        ])
    
    @property
    def separator(self) -> str:
        """Get the separator between prompt parts."""
        return getattr(self._config, "default_separator", ". ")
    
    @property
    def max_length(self) -> int:
        """Get max prompt length."""
        return getattr(self._config, "max_prompt_length", 500)
    
    def get_camera_term(self, key: str) -> str:
        """Map camera key to model-specific vocabulary."""
        vocab = getattr(self._config, "camera_vocabulary", {})
        return vocab.get(key.lower().replace(" ", "_").replace("-", "_"), key)
    
    def get_lighting_term(self, key: str) -> str:
        """Map lighting key to model-specific vocabulary."""
        vocab = getattr(self._config, "lighting_vocabulary", {})
        return vocab.get(key.lower().replace(" ", "_").replace("-", "_"), key)
    
    def get_negative_prompt(self) -> str:
        """Get default negative prompt for this model."""
        return getattr(self._config, "negative_prompt", "")
    
    def validate_prompt(self, prompt: StructuredPrompt) -> list[str]:
        """
        Validate prompt against model-specific constraints.
        
        Returns:
            List of warning messages (empty if valid)
        """
        warnings = []
        compiled = self.compile(prompt)
        
        if len(compiled) > self.max_length:
            warnings.append(
                f"Prompt exceeds max length ({len(compiled)} > {self.max_length})"
            )
        
        return warnings
