"""
API request/response schemas.

All Pydantic models for API validation and serialization.
Separate from domain models (in models/) - these are API contracts.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from ingest_core.models import AssetStatus, AssetType, LineageType

# =============================================================================
# Asset Schemas
# =============================================================================

class AssetResponse(BaseModel):
    """API response for asset data."""
    id: UUID
    asset_type: AssetType
    status: AssetStatus
    original_filename: str
    file_extension: str
    file_size_bytes: int
    mime_type: str
    storage_path: str
    created_at: datetime
    updated_at: datetime
    processed_at: datetime | None = None
    error_message: str | None = None
    extra_metadata: dict[str, Any] = Field(default_factory=dict)
    embedding_id: str | None = None

    class Config:
        from_attributes = True


class AssetListResponse(BaseModel):
    """Paginated list of assets."""
    items: list[AssetResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# =============================================================================
# Analysis Schemas
# =============================================================================

class AnalyzeRequest(BaseModel):
    """Request to analyze an asset."""
    analyzers: list[str] | None = Field(
        default=None,
        description="Specific analyzers to run. None = all applicable."
    )
    force: bool = Field(
        default=False,
        description="Re-run even if already analyzed."
    )
    callback_url: str | None = Field(
        default=None,
        description="Webhook URL for completion notification."
    )


class AnalyzeResponse(BaseModel):
    """Response from analysis request."""
    asset_id: UUID
    status: str  # "queued", "processing", "completed", "failed"
    analyzers_triggered: list[str]
    message: str


# =============================================================================
# Lineage Schemas
# =============================================================================

class LineageCreateRequest(BaseModel):
    """Request to create lineage relationship."""
    source_asset_id: UUID
    target_asset_id: UUID
    relationship_type: LineageType
    description: str | None = None
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Generation params, model config, etc."
    )


class LineageResponse(BaseModel):
    """Lineage record response."""
    id: UUID
    source_asset_id: UUID
    target_asset_id: UUID
    relationship_type: LineageType
    description: str | None
    metadata: dict[str, Any]
    created_at: datetime
    created_by: str | None

    class Config:
        from_attributes = True


# =============================================================================
# Search Schemas
# =============================================================================

class SearchRequest(BaseModel):
    """Search request with multiple strategies."""
    # Text search
    query: str | None = Field(default=None, description="Text search in descriptions/tags")

    # Similarity search
    similar_to: UUID | None = Field(default=None, description="Find assets similar to this ID")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

    # Filters
    asset_types: list[AssetType] | None = None
    status: AssetStatus | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    tags: list[str] | None = Field(default=None, description="Filter by tags (AND)")

    # Pagination
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SearchResponse(BaseModel):
    """Search results with relevance scores."""
    items: list[dict[str, Any]]  # Asset + score
    total: int
    page: int
    page_size: int
    search_strategy: str  # "text", "similarity", "hybrid"


# =============================================================================
# Batch Schemas
# =============================================================================

class BatchUploadResponse(BaseModel):
    """Response for batch upload."""
    successful: list[AssetResponse]
    failed: list[dict[str, str]]  # filename -> error
    total: int


# =============================================================================
# Health & Error Schemas
# =============================================================================

class HealthResponse(BaseModel):
    """System health status."""
    status: str
    version: str
    database: str
    vector_db: str
    storage: str
    analyzers_loaded: list[str]


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: str | None = None
    code: str | None = None