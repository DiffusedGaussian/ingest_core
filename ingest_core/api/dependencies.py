"""
FastAPI dependency injection.

Provides container access to all route handlers.
"""

from typing import Annotated

from fastapi import Depends

from ingest_core.container import get_container
from ingest_core.container.container import Container


async def get_container_dep() -> Container:
    """
    FastAPI dependency for container access.

    Usage in routes:
        @router.get("/example")
        async def example(container: ContainerDep):
            return container.settings.env
    """
    return get_container()


# Type alias for cleaner route signatures
ContainerDep = Annotated[Container, Depends(get_container_dep)]
