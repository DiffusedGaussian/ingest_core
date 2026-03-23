"""
Pipeline Routes - End-to-end workflows.

This is the MAIN ENTRY POINT for the pipeline. It orchestrates:
1. Image upload → Asset creation
2. VLM analysis → Extract scene/subject/style
3. Prompt generation → Create video prompt
4. (Optional) Video generation → Call Runway/Kling/etc.
5. Lineage tracking → Connect inputs to outputs

Example usage:
    # Upload and process in one call
    curl -X POST "http://localhost:8000/api/v1/pipeline/process" \
        -F "file=@my_image.jpg" \
        -F "generator=runway" \
        -F "duration=5"
    
    # Response includes asset, analysis, and generated prompt
"""

from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, BackgroundTasks
from pydantic import BaseModel, Field
from structlog import get_logger

from ingest_core.api.dependencies import get_container
from ingest_core.models.video_prompt import (
    CameraMovement,
    GeneratedVideoPrompt,
    MovementSpeed,
    VideoPromptAnalysis,
)

logger = get_logger()
router = APIRouter(prefix="/pipeline", tags=["pipeline"])


# =============================================================================
# Schemas
# =============================================================================

class PipelineResult(BaseModel):
    """Result of the full pipeline execution."""
    
    asset_id: UUID = Field(description="ID of the created/processed asset")
    status: str = Field(description="Pipeline status: success, partial, error")
    
    # Analysis results
    analysis: dict[str, Any] | None = Field(
        default=None,
        description="VLM analysis results (subject, scene, style, etc.)"
    )
    
    # Generated prompt
    prompt: str | None = Field(
        default=None,
        description="Generated video prompt ready for Runway/Kling/etc."
    )
    prompt_details: dict[str, Any] | None = Field(
        default=None,
        description="Full prompt details including components and recommendations"
    )
    
    # Generation result (if requested)
    generation: dict[str, Any] | None = Field(
        default=None,
        description="Video generation result (if generation was requested)"
    )
    
    # Errors (if any)
    errors: list[str] = Field(
        default_factory=list,
        description="Any errors encountered during processing"
    )


class ProcessRequest(BaseModel):
    """Request body for processing an existing asset."""
    
    asset_id: UUID = Field(description="Asset ID to process")
    generator: str = Field(default="runway", description="Target generator: runway, kling, flux")
    duration: int = Field(default=5, ge=1, le=60, description="Video duration in seconds")
    camera_movement: CameraMovement | None = Field(default=None, description="Override camera movement")
    movement_speed: MovementSpeed | None = Field(default=None, description="Override movement speed")
    template_id: str | None = Field(default=None, description="Use a specific prompt template")
    generate_video: bool = Field(default=False, description="Actually generate video (requires API keys)")


class BatchProcessRequest(BaseModel):
    """Request for batch processing multiple assets."""
    
    asset_ids: list[UUID] = Field(description="List of asset IDs to process")
    generator: str = Field(default="runway")
    duration: int = Field(default=5, ge=1, le=60)


class BatchProcessResult(BaseModel):
    """Result of batch processing."""
    
    total: int
    successful: int
    failed: int
    results: list[PipelineResult]


# =============================================================================
# Routes
# =============================================================================

@router.post(
    "/upload_and_process",
    response_model=PipelineResult,
    summary="Upload image and run full pipeline",
    description="""
    **One-shot endpoint**: Upload an image and get back a video-ready prompt.
    
    This is the main entry point for the pipeline. It:
    1. Creates an asset from the uploaded file
    2. Runs VLM analysis to understand the image
    3. Generates an optimized video prompt
    4. Optionally triggers video generation
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/pipeline/upload-and-process" \\
        -F "file=@sunset_beach.jpg" \\
        -F "generator=runway" \\
        -F "duration=5"
    ```
    
    **Response:**
    ```json
    {
        "asset_id": "abc123...",
        "status": "success",
        "prompt": "A serene sunset over a calm beach. Slow camera pushes in...",
        "analysis": { ... }
    }
    ```
    """,
)
async def upload_and_process(
    file: Annotated[UploadFile, File(description="Image file to process")],
    generator: Annotated[str, Form(description="Target generator")] = "runway",
    duration: Annotated[int, Form(description="Video duration", ge=1, le=60)] = 5,
    camera_movement: Annotated[str | None, Form(description="Camera movement override")] = None,
    template_id: Annotated[str | None, Form(description="Prompt template ID")] = None,
    generate_video: Annotated[bool, Form(description="Trigger video generation")] = False,
):
    """Upload and process in one call."""
    container = get_container()
    errors = []
    
    # 1. Create asset from upload
    logger.info("Pipeline: Creating asset", filename=file.filename)
    
    try:
        # Read file content
        content = await file.read()
        
        # Determine asset type from extension
        suffix = Path(file.filename or "image.jpg").suffix.lower()
        asset_type = "image"
        if suffix in [".mp4", ".mov", ".avi", ".webm"]:
            asset_type = "video"
        elif suffix in [".obj", ".fbx", ".glb", ".gltf"]:
            asset_type = "asset_3d"
        
        # Create asset through ingestion service
        asset = await container.ingestion_service.ingest_bytes(
            content=content,
            filename=file.filename or "uploaded_file",
            asset_type=asset_type,
        )
        asset_id = asset.id
        logger.info("Pipeline: Asset created", asset_id=str(asset_id))
        
    except Exception as e:
        logger.error("Pipeline: Asset creation failed", error=str(e))
        raise HTTPException(status_code=400, detail=f"Failed to create asset: {e}")
    
    # 2. Run VLM analysis
    analysis_dict = None
    try:
        logger.info("Pipeline: Running VLM analysis", asset_id=str(asset_id))
        analysis = await container.prompt_generator.analyze_image(asset_id)
        analysis_dict = analysis.model_dump(mode="json")
        logger.info("Pipeline: Analysis complete", asset_id=str(asset_id))
    except Exception as e:
        logger.warning("Pipeline: Analysis failed", error=str(e))
        errors.append(f"Analysis failed: {e}")
    
    # 3. Generate prompt
    prompt_text = None
    prompt_details = None
    try:
        logger.info("Pipeline: Generating prompt", asset_id=str(asset_id), generator=generator)
        
        # Parse camera movement if provided
        cam = None
        if camera_movement:
            try:
                cam = CameraMovement(camera_movement)
            except ValueError:
                errors.append(f"Invalid camera movement: {camera_movement}")
        
        # Generate prompt (with or without template)
        if template_id:
            prompt_result = await container.prompt_generator.generate_prompt_with_template(
                asset_id=asset_id,
                template_id=template_id,
                duration=duration,
                target_generator=generator,
            )
        else:
            prompt_result = await container.prompt_generator.generate_prompt(
                asset_id=asset_id,
                camera_movement=cam,
                duration=duration,
                target_generator=generator,
            )
        
        prompt_text = prompt_result.prompt
        prompt_details = prompt_result.model_dump(mode="json")
        logger.info("Pipeline: Prompt generated", asset_id=str(asset_id), prompt_length=len(prompt_text))
        
    except Exception as e:
        logger.warning("Pipeline: Prompt generation failed", error=str(e))
        errors.append(f"Prompt generation failed: {e}")
    
    # 4. Optionally generate video
    generation_result = None
    if generate_video and prompt_text:
        try:
            logger.info("Pipeline: Triggering video generation", generator=generator)
            generation_result = await _trigger_generation(
                container=container,
                prompt=prompt_text,
                generator=generator,
                duration=duration,
                source_asset_id=asset_id,
            )
        except Exception as e:
            logger.warning("Pipeline: Video generation failed", error=str(e))
            errors.append(f"Video generation failed: {e}")
    
    # Determine status
    status = "success"
    if errors:
        status = "partial" if prompt_text else "error"
    
    return PipelineResult(
        asset_id=asset_id,
        status=status,
        analysis=analysis_dict,
        prompt=prompt_text,
        prompt_details=prompt_details,
        generation=generation_result,
        errors=errors,
    )


@router.post(
    "/process",
    response_model=PipelineResult,
    summary="Process an existing asset",
    description="Run the pipeline on an already-uploaded asset.",
)
async def process_asset(request: ProcessRequest):
    """Process an existing asset through the pipeline."""
    container = get_container()
    errors = []
    
    # Verify asset exists
    asset = await container.asset_service.get(request.asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {request.asset_id} not found")
    
    # Run analysis
    analysis_dict = None
    try:
        analysis = await container.prompt_generator.analyze_image(request.asset_id)
        analysis_dict = analysis.model_dump(mode="json")
    except Exception as e:
        errors.append(f"Analysis failed: {e}")
    
    # Generate prompt
    prompt_text = None
    prompt_details = None
    try:
        if request.template_id:
            prompt_result = await container.prompt_generator.generate_prompt_with_template(
                asset_id=request.asset_id,
                template_id=request.template_id,
                duration=request.duration,
                target_generator=request.generator,
            )
        else:
            prompt_result = await container.prompt_generator.generate_prompt(
                asset_id=request.asset_id,
                camera_movement=request.camera_movement,
                movement_speed=request.movement_speed,
                duration=request.duration,
                target_generator=request.generator,
            )
        
        prompt_text = prompt_result.prompt
        prompt_details = prompt_result.model_dump(mode="json")
    except Exception as e:
        errors.append(f"Prompt generation failed: {e}")
    
    # Optionally generate video
    generation_result = None
    if request.generate_video and prompt_text:
        try:
            generation_result = await _trigger_generation(
                container=container,
                prompt=prompt_text,
                generator=request.generator,
                duration=request.duration,
                source_asset_id=request.asset_id,
            )
        except Exception as e:
            errors.append(f"Video generation failed: {e}")
    
    status = "success" if not errors else ("partial" if prompt_text else "error")
    
    return PipelineResult(
        asset_id=request.asset_id,
        status=status,
        analysis=analysis_dict,
        prompt=prompt_text,
        prompt_details=prompt_details,
        generation=generation_result,
        errors=errors,
    )


@router.post(
    "/batch",
    response_model=BatchProcessResult,
    summary="Process multiple assets",
    description="Run the pipeline on multiple assets in parallel.",
)
async def batch_process(request: BatchProcessRequest, background_tasks: BackgroundTasks):
    """Process multiple assets."""
    container = get_container()
    results = []
    
    for asset_id in request.asset_ids:
        try:
            result = await process_asset(ProcessRequest(
                asset_id=asset_id,
                generator=request.generator,
                duration=request.duration,
            ))
            results.append(result)
        except Exception as e:
            results.append(PipelineResult(
                asset_id=asset_id,
                status="error",
                errors=[str(e)],
            ))
    
    successful = sum(1 for r in results if r.status == "success")
    failed = sum(1 for r in results if r.status == "error")
    
    return BatchProcessResult(
        total=len(request.asset_ids),
        successful=successful,
        failed=failed,
        results=results,
    )


@router.get(
    "/status/{asset_id}",
    summary="Get pipeline status for an asset",
    description="Check if an asset has been processed and get results.",
)
async def get_pipeline_status(asset_id: UUID):
    """Get the pipeline status for an asset."""
    container = get_container()
    
    asset = await container.asset_service.get(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Check what's been processed
    analysis = asset.extra_metadata.get("video_prompt_analysis")
    prompt = asset.extra_metadata.get("video_prompt_latest")
    
    return {
        "asset_id": asset_id,
        "has_analysis": analysis is not None,
        "has_prompt": prompt is not None,
        "analysis": analysis,
        "prompt": prompt.get("prompt") if prompt else None,
        "prompt_details": prompt,
    }


@router.get(
    "/templates",
    summary="List available prompt templates",
    description="Get all available prompt templates with their descriptions.",
)
async def list_templates():
    """List available prompt templates."""
    from ingest_core.models.prompt_template import TEMPLATES
    
    return {
        "templates": [
            {
                "id": tid,
                "name": t.name,
                "description": t.description,
                "defaults": t.defaults,
            }
            for tid, t in TEMPLATES.items()
        ]
    }


# =============================================================================
# Internal Helpers
# =============================================================================

async def _trigger_generation(
    container,
    prompt: str,
    generator: str,
    duration: int,
    source_asset_id: UUID,
) -> dict[str, Any]:
    """
    Trigger video generation via external API.
    
    This is a placeholder that shows the integration point.
    In production, this would call Runway/Kling/Flux APIs.
    """
    # Check if we have the adapter
    try:
        if generator == "kling":
            from ingest_core.adapters.kling import KlingAdapter
            adapter = KlingAdapter(container.settings)
            result = await adapter.generate(prompt=prompt, duration=duration)
            
            # Create lineage record
            if result.get("video_url"):
                # Track that this video came from the source image
                await container.lineage_service.create_lineage(
                    parent_id=source_asset_id,
                    child_id=result.get("generation_id"),
                    relationship_type="generated_from",
                    metadata={
                        "generator": generator,
                        "prompt": prompt,
                        "duration": duration,
                    },
                )
            
            return result
        else:
            # Placeholder for other generators
            return {
                "status": "pending",
                "generator": generator,
                "prompt": prompt,
                "duration": duration,
                "message": f"Generation with {generator} not yet implemented. Prompt is ready to use.",
            }
    except ImportError:
        return {
            "status": "unavailable",
            "generator": generator,
            "message": f"Adapter for {generator} not available",
            "prompt": prompt,
        }
    except Exception as e:
        return {
            "status": "error",
            "generator": generator,
            "error": str(e),
            "prompt": prompt,
        }
