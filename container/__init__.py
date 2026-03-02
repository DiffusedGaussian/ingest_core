"""
Dependency Injection Container module.

Provides a centralized container for managing dependencies:
- Database connections
- Storage backends
- Analyzers
- Services

Uses a simple registry pattern for DI without external frameworks.
"""

from container.container import Container, get_container

__all__ = ["Container", "get_container"]