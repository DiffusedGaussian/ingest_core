"""Video prompt generation endpoints."""
import csv
import io
from typing import Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from ingest_core.api.dependencies import ContainerDep
from ingest_core.models.video_prompt import CameraMovement, MovementSpeed
from ingest_core.models.prompt_template import TEMPLATES, PromptTemplate

router = APIRouter(tags=["prompts"])

class GeneratePromptRequest(BaseModel):
    camera_movement: CameraMovement | None = None
    movement_speed: MovementSpeed | None = None
    duration: int = Field(default=5, ge=1, le=30)
    target_generator: str = "flux"

class PromptResponse(BaseModel):
    asset_id: UUID
    prompt: str
    prompt_components: dict
    recommended_camera: str | None
    recommended_speed: str
    recommended_duration: int
    target_generator: str
    variations: list[str] = []

@router.post("/assets/{asset_id}/generate-prompt", response_model=PromptResponse)
async def generate_video_prompt(asset_id: UUID, container: ContainerDep, request: GeneratePromptRequest | None = None) -> PromptResponse:
    """Generate an optimized video prompt for an image."""
    request = request or GeneratePromptRequest()
    try:
        result = await container.prompt_generator.generate_prompt(
            asset_id=asset_id, camera_movement=request.camera_movement,
            movement_speed=request.movement_speed, duration=request.duration,
            target_generator=request.target_generator,
        )
        return PromptResponse(
            asset_id=asset_id, prompt=result.prompt, prompt_components=result.prompt_components,
            recommended_camera=result.recommended_camera.value if result.recommended_camera else None,
            recommended_speed=result.recommended_speed.value, recommended_duration=result.recommended_duration,
            target_generator=result.target_generator, variations=result.variations,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

@router.get("/assets/{asset_id}/prompt", response_model=PromptResponse | None)
async def get_latest_prompt(asset_id: UUID, container: ContainerDep) -> PromptResponse | None:
    """Get the most recently generated prompt."""
    asset = await container.asset_service.get(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
    latest = asset.extra_metadata.get("video_prompt_latest")
    if not latest:
        return None
    return PromptResponse(
        asset_id=asset_id, prompt=latest.get("prompt", ""),
        prompt_components=latest.get("prompt_components", {}),
        recommended_camera=latest.get("recommended_camera"),
        recommended_speed=latest.get("recommended_speed", "slow"),
        recommended_duration=latest.get("recommended_duration", 5),
        target_generator=latest.get("target_generator", "flux"),
        variations=latest.get("variations", []),
    )


@router.get("/prompts/export")
async def export_prompts(
    container: ContainerDep,
    format: str = Query(default="json", regex="^(json|csv)$"),
    limit: int = Query(default=1000, ge=1, le=10000),
) -> Any:
    """Export all generated prompts to JSON or CSV format."""
    assets, _ = await container.db.list_assets(limit=limit)
    
    prompts = []
    for asset in assets:
        latest = asset.extra_metadata.get("video_prompt_latest")
        if latest:
            prompts.append({
                "asset_id": str(asset.id),
                "filename": asset.original_filename,
                "prompt": latest.get("prompt", ""),
                "camera": latest.get("recommended_camera", ""),
                "speed": latest.get("recommended_speed", ""),
                "duration": latest.get("recommended_duration", 5),
                "generator": latest.get("target_generator", "flux"),
            })
    
    if format == "csv":
        output = io.StringIO()
        if prompts:
            writer = csv.DictWriter(output, fieldnames=prompts[0].keys())
            writer.writeheader()
            writer.writerows(prompts)
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=prompts.csv"}
        )
    
    return {"prompts": prompts, "count": len(prompts)}


@router.get("/templates", response_model=list[PromptTemplate])
async def list_templates() -> list[PromptTemplate]:
    """List all available prompt templates."""
    return list(TEMPLATES.values())


@router.get("/templates/{template_id}", response_model=PromptTemplate)
async def get_template(template_id: str) -> PromptTemplate:
    """Get a specific template by ID."""
    if template_id not in TEMPLATES:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    return TEMPLATES[template_id]


class GenerateWithTemplateRequest(BaseModel):
    template_id: str = "default"
    overrides: dict[str, str] = Field(default_factory=dict)
    duration: int = Field(default=5, ge=1, le=30)
    target_generator: str = "flux"


@router.post("/assets/{asset_id}/generate-prompt-with-template", response_model=PromptResponse)
async def generate_prompt_with_template(
    asset_id: UUID,
    container: ContainerDep,
    request: GenerateWithTemplateRequest,
) -> PromptResponse:
    """Generate a prompt using a custom template."""
    if request.template_id not in TEMPLATES:
        raise HTTPException(status_code=404, detail=f"Template '{request.template_id}' not found")
    
    try:
        result = await container.prompt_generator.generate_prompt_with_template(
            asset_id=asset_id,
            template_id=request.template_id,
            overrides=request.overrides,
            duration=request.duration,
            target_generator=request.target_generator,
        )
        return PromptResponse(
            asset_id=asset_id,
            prompt=result.prompt,
            prompt_components=result.prompt_components,
            recommended_camera=result.recommended_camera.value if result.recommended_camera else None,
            recommended_speed=result.recommended_speed.value if result.recommended_speed else "slow",
            recommended_duration=result.recommended_duration,
            target_generator=result.target_generator,
            variations=result.variations,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
