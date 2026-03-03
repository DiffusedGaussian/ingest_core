"""
Asset CRUD endpoints.

Handles upload, list, get, delete, and download operations.
"""

from typing import Any
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse

from ingest_core.api.dependencies import ContainerDep

# Import for background analysis
from ingest_core.api.routes.analysis import run_analysis_pipeline
from ingest_core.api.schemas import (
    AssetListResponse,
    AssetResponse,
    BatchUploadResponse,
    ErrorResponse,
)
from ingest_core.models import Asset, AssetStatus, AssetType

router = APIRouter(tags=["assets"])


@router.post(
    "/assets",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new asset",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file"},
        413: {"model": ErrorResponse, "description": "File too large"},
    },
)
async def upload_asset(
    container: ContainerDep,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Media file to upload"),  # noqa: B008
    tags: str | None = Form(default=None, description="Comma-separated tags"),
    auto_analyze: bool = Form(default=True, description="Run analyzers after upload"),
) -> AssetResponse:
    """
    Upload a new media asset (image, video, or 3D file).

    The asset will be:
    1. Validated for file type and size
    2. Stored in the configured backend (local/GCS)
    3. Registered in the database
    4. Optionally analyzed in the background

    Supported formats:
    - Images: JPEG, PNG, WebP, GIF, TIFF, BMP
    - Videos: MP4, MOV, AVI, WebM, MKV (max 30s)
    - 3D: GLB, GLTF, OBJ, FBX, USD
    """
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    if not file.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content-Type is required",
        )

    # Check file size
    max_size = container.settings.processing.max_file_size_mb * 1024 * 1024
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {container.settings.processing.max_file_size_mb}MB",
        )

    # Reset file position for ingestion
    await file.seek(0)

    # Ingest the file
    try:
        asset = await container.ingestion_service.ingest_file(
            file_obj=file.file,
            filename=file.filename,
            content_type=file.content_type,
        )
    except Exception as e:
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ingestion failed: {str(e)}",
        )

    # Add tags if provided
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        asset.extra_metadata["tags"] = tag_list
        # Persist tags to DB
        db = container.db
        if container.settings.database_backend == "mongodb":
            await db.assets.update_one(
                {"_id": str(asset.id)},
                {"$set": {"extra_metadata": asset.extra_metadata}}
            )
        else:
            await db.update_asset_metadata(asset.id, asset.extra_metadata)

    # Schedule background analysis
    if auto_analyze:
        background_tasks.add_task(
            run_analysis_pipeline,
            container,
            asset.id,
            analyzers=None,
        )

    return AssetResponse.model_validate(asset)


@router.get(
    "/assets",
    response_model=AssetListResponse,
    summary="List all assets",
)
async def list_assets(
    container: ContainerDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    asset_type: AssetType | None = Query(default=None),
    status_filter: AssetStatus | None = Query(default=None, alias="status"),
) -> AssetListResponse:
    """
    List assets with pagination and filtering.
    """
    # Build query
    query: dict[str, Any] = {}
    if asset_type:
        query["asset_type"] = asset_type.value
    if status_filter:
        query["status"] = status_filter.value

    skip = (page - 1) * page_size
    db = container.db

    if container.settings.database_backend == "mongodb":
        cursor = db.assets.find(query).skip(skip).limit(page_size)
        items = [Asset.model_validate(doc) async for doc in cursor]
        total = await db.assets.count_documents(query)
    else:
        items, total = await db.list_assets(
            query=query,
            skip=skip,
            limit=page_size,
        )

    return AssetListResponse(
        items=[AssetResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(skip + len(items)) < total,
    )


@router.get(
    "/assets/{asset_id}",
    response_model=AssetResponse,
    summary="Get asset by ID",
    responses={404: {"model": ErrorResponse}},
)
async def get_asset(
    asset_id: UUID,
    container: ContainerDep,
) -> AssetResponse:
    """
    Retrieve a single asset by ID.

    Returns full metadata including analysis results.
    """
    asset = await container.asset_service.get(asset_id)

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset {asset_id} not found",
        )

    return AssetResponse.model_validate(asset)


@router.delete(
    "/assets/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete asset",
    responses={404: {"model": ErrorResponse}},
)
async def delete_asset(
    asset_id: UUID,
    container: ContainerDep,
) -> None:
    """
    Delete an asset and all associated data.

    This removes:
    - The file from storage
    - The database record
    - Vector embeddings
    - Lineage records (optional)
    """
    deleted = await container.asset_service.delete(asset_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset {asset_id} not found",
        )


@router.get(
    "/assets/{asset_id}/download",
    summary="Download asset file",
    responses={404: {"model": ErrorResponse}},
)
async def download_asset(
    asset_id: UUID,
    container: ContainerDep,
) -> StreamingResponse:
    """
    Download the original asset file.
    """
    asset = await container.asset_service.get(asset_id)

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset {asset_id} not found",
        )

    async def file_stream():
        async for chunk in container.storage.get(asset.storage_path):
            yield chunk

    return StreamingResponse(
        file_stream(),
        media_type=asset.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{asset.original_filename}"'
        },
    )


@router.post(
    "/assets/batch",
    response_model=BatchUploadResponse,
    summary="Upload multiple assets",
)
async def batch_upload(
    container: ContainerDep,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(..., description="Multiple files to upload"),
    auto_analyze: bool = Form(default=True),
) -> BatchUploadResponse:
    """
    Upload multiple assets in a single request.

    Useful for uploading training data or multiple reference images.
    """
    successful = []
    failed = []

    for file in files:
        try:
            if not file.filename or not file.content_type:
                failed.append({
                    "filename": file.filename or "unknown",
                    "error": "Missing filename or content-type",
                })
                continue

            asset = await container.ingestion_service.ingest_file(
                file_obj=file.file,
                filename=file.filename,
                content_type=file.content_type,
            )
            successful.append(AssetResponse.model_validate(asset))

            if auto_analyze:
                background_tasks.add_task(
                    run_analysis_pipeline,
                    container,
                    asset.id,
                    analyzers=None,
                )
        except Exception as e:
            failed.append({
                "filename": file.filename or "unknown",
                "error": str(e),
            })

    return BatchUploadResponse(
        successful=successful,
        failed=failed,
        total=len(files),
    )