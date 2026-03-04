"""Lineage tracking endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from ingest_core.api.dependencies import ContainerDep
from ingest_core.models.lineage import LineageType

router = APIRouter(tags=["lineage"])


class LineageCreateRequest(BaseModel):
    """Request to create lineage relationship."""

    source_asset_id: UUID
    target_asset_id: UUID
    relationship_type: LineageType
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LineageResponse(BaseModel):
    """Lineage record response."""

    id: UUID
    source_asset_id: UUID
    target_asset_id: UUID
    relationship_type: LineageType
    description: str | None
    metadata: dict[str, Any]
    created_at: str
    created_by: str | None = None

    class Config:
        from_attributes = True


@router.post(
    "/lineage",
    response_model=LineageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create lineage relationship",
)
async def create_lineage(
    request: LineageCreateRequest,
    container: ContainerDep,
) -> LineageResponse:
    """Record a lineage relationship between assets."""
    source = await container.asset_service.get(request.source_asset_id)
    target = await container.asset_service.get(request.target_asset_id)

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source asset {request.source_asset_id} not found",
        )
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target asset {request.target_asset_id} not found",
        )

    records = await container.lineage_service.record_generation(
        source_ids=[request.source_asset_id],
        output_id=request.target_asset_id,
        generator="manual",
        description=request.description,
    )

    record = records[0]
    return LineageResponse(
        id=record.id,
        source_asset_id=record.source_asset_id,
        target_asset_id=record.target_asset_id,
        relationship_type=record.relationship_type,
        description=record.description,
        metadata=record.metadata,
        created_at=record.created_at.isoformat(),
        created_by=record.created_by,
    )


@router.get(
    "/assets/{asset_id}/lineage",
    response_model=list[LineageResponse],
    summary="Get asset lineage",
)
async def get_asset_lineage(
    asset_id: UUID,
    container: ContainerDep,
    direction: str = Query(
        default="both",
        pattern="^(sources|outputs|both)$",
    ),
) -> list[LineageResponse]:
    """Get lineage relationships for an asset."""
    records = await container.lineage_service.get_lineage_records(asset_id, direction)

    return [
        LineageResponse(
            id=r.id,
            source_asset_id=r.source_asset_id,
            target_asset_id=r.target_asset_id,
            relationship_type=r.relationship_type,
            description=r.description,
            metadata=r.metadata,
            created_at=r.created_at.isoformat(),
            created_by=r.created_by,
        )
        for r in records
    ]