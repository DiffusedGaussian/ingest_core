"""
Analysis pipeline endpoints.

Handles triggering and running analyzers on assets.
"""

import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from ingest_core.api.dependencies import ContainerDep
from ingest_core.api.schemas import AnalyzeRequest, AnalyzeResponse, ErrorResponse
from ingest_core.container.container import Container

router = APIRouter(tags=["analysis"])


@router.post(
    "/assets/{asset_id}/analyze",
    response_model=AnalyzeResponse,
    summary="Trigger analysis pipeline",
    responses={404: {"model": ErrorResponse}},
)
async def analyze_asset(
    asset_id: UUID,
    container: ContainerDep,
    background_tasks: BackgroundTasks,
    request: AnalyzeRequest | None = None,
) -> AnalyzeResponse:
    """
    Run analysis pipeline on an asset.

    Available analyzers:
    - `exif`: Extract EXIF metadata (images)
    - `phash`: Compute perceptual hash for deduplication
    - `objects`: Detect objects in image
    - `vlm`: Generate rich description via vision-language model

    Analysis runs in the background. Poll the asset endpoint
    or provide a callback_url for completion notification.
    """
    request = request or AnalyzeRequest()

    # Check asset exists
    asset = await container.asset_service.get(asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset {asset_id} not found",
        )

    # Determine which analyzers to run
    if request.analyzers:
        available = set(container.analyzers.keys())
        requested = set(request.analyzers)
        invalid = requested - available
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown analyzers: {invalid}. Available: {available}",
            )
        analyzers_to_run = request.analyzers
    else:
        # Run all applicable analyzers
        analyzers_to_run = [
            name for name, analyzer in container.analyzers.items()
            if analyzer.supports(asset.asset_type.value)
        ]

    # Skip if already analyzed (unless forced)
    if not request.force:
        already_run = set(asset.extra_metadata.get("analyzers_completed", []))
        analyzers_to_run = [a for a in analyzers_to_run if a not in already_run]

    if not analyzers_to_run:
        return AnalyzeResponse(
            asset_id=asset_id,
            status="completed",
            analyzers_triggered=[],
            message="All requested analyzers already completed. Use force=true to re-run.",
        )

    # Queue background analysis
    background_tasks.add_task(
        run_analysis_pipeline,
        container,
        asset_id,
        analyzers=analyzers_to_run,
        callback_url=request.callback_url,
    )

    return AnalyzeResponse(
        asset_id=asset_id,
        status="queued",
        analyzers_triggered=analyzers_to_run,
        message=f"Analysis queued for {len(analyzers_to_run)} analyzer(s).",
    )


async def run_analysis_pipeline(
    container: Container,
    asset_id: UUID,
    analyzers: list[str] | None = None,
    callback_url: str | None = None,
) -> None:
    """
    Background task to run analysis pipeline.

    Downloads asset to temp file, runs each analyzer,
    updates asset metadata, and optionally calls webhook.
    """
    asset = await container.asset_service.get(asset_id)
    if not asset:
        return

    # Download to temp file
    temp_dir = Path(tempfile.mkdtemp())
    temp_path = temp_dir / f"{asset_id}{asset.file_extension}"

    try:
        # Stream file from storage
        async for chunk in container.storage.get(asset.storage_path):
            with open(temp_path, "ab") as f:
                f.write(chunk)

        # Determine analyzers to run
        if analyzers is None:
            analyzers = [
                name for name, analyzer in container.analyzers.items()
                if analyzer.supports(asset.asset_type.value)
            ]

        results = {}
        completed = []

        # Run each analyzer
        for analyzer_name in analyzers:
            analyzer = container.get_analyzer(analyzer_name)
            try:
                result = await analyzer.analyze(
                    temp_path,
                    asset.asset_type.value,
                )
                if result.success:
                    results[analyzer_name] = result.data
                    completed.append(analyzer_name)
                else:
                    results[analyzer_name] = {"error": result.error}
            except Exception as e:
                results[analyzer_name] = {"error": str(e)}

        # Update asset with results
        asset.extra_metadata.update(results)
        asset.extra_metadata["analyzers_completed"] = list(
            set(asset.extra_metadata.get("analyzers_completed", []) + completed)
        )

        # Save to database
        db = container.db
        if container.settings.database_backend == "mongodb":
            await db.assets.update_one(
                {"_id": str(asset_id)},
                {"$set": {"extra_metadata": asset.extra_metadata}}
            )
        else:
            await db.update_asset_metadata(asset_id, asset.extra_metadata)

        # Webhook callback if provided
        if callback_url:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(callback_url, json={
                    "asset_id": str(asset_id),
                    "status": "completed",
                    "analyzers": completed,
                })

    finally:
        # Cleanup temp files
        if temp_path.exists():
            temp_path.unlink()
        temp_dir.rmdir()