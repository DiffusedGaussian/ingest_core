"""
Flux Image Generation Service.

Integrates with Black Forest Labs API (api.bfl.ml) for image generation.
Supports both text-to-image and image-to-image workflows.
"""

import asyncio
import base64
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import httpx
from structlog import get_logger

if TYPE_CHECKING:
    from ingest_core.container.container import Container

logger = get_logger()

BFL_API_BASE = "https://api.bfl.ml/v1"


class FluxGeneratorService:
    """
    Generate images using Black Forest Labs Flux API.
    
    Supports:
    - flux-pro-1.1: High quality text-to-image
    - flux-pro-1.1-ultra: Highest quality
    - flux-kontext-pro: Image-to-image with context
    """
    
    def __init__(self, container: "Container"):
        self.container = container
        self._api_key = None
    
    @property
    def api_key(self) -> str:
        """Get BFL API key from environment."""
        if self._api_key is None:
            import os
            self._api_key = os.getenv("BFL_API_KEY")
            if not self._api_key:
                raise ValueError("BFL_API_KEY not set in environment")
        return self._api_key
    
    async def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        model: str = "flux-pro-1.1",
        safety_tolerance: int = 2,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Generate an image from a text prompt.
        
        Args:
            prompt: The text prompt for generation
            width: Image width (default 1024)
            height: Image height (default 1024)
            model: Model to use (flux-pro-1.1, flux-pro-1.1-ultra, flux-dev)
            safety_tolerance: 0-6, higher = more permissive
            
        Returns:
            dict with 'image_url', 'task_id', 'status'
        """
        logger.info("Flux: Starting generation", model=model, prompt_length=len(prompt))
        
        # Submit generation task
        task_id = await self._submit_task(
            endpoint=model,
            payload={
                "prompt": prompt,
                "width": width,
                "height": height,
                "safety_tolerance": safety_tolerance,
                **kwargs,
            }
        )
        
        # Poll for result
        result = await self._poll_result(task_id)
        
        return {
            "task_id": task_id,
            "status": "completed",
            "image_url": result.get("sample"),
            "seed": result.get("seed"),
            "model": model,
            "prompt": prompt,
        }
    
    async def generate_image_to_image(
        self,
        prompt: str,
        source_image_path: Path | str,
        strength: float = 0.75,
        width: int = 1024,
        height: int = 1024,
        model: str = "flux-kontext-pro",
        **kwargs,
    ) -> dict[str, Any]:
        """
        Generate an image using another image as reference (img2img).
        
        Args:
            prompt: The text prompt describing the transformation
            source_image_path: Path to the source image
            strength: How much to transform (0=no change, 1=complete reimagining)
            width: Output width
            height: Output height
            model: Model to use (flux-kontext-pro recommended for img2img)
            
        Returns:
            dict with 'image_url', 'task_id', 'status'
        """
        logger.info("Flux: Starting img2img generation", model=model, strength=strength)
        
        # Read and encode source image
        source_path = Path(source_image_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Source image not found: {source_path}")
        
        with open(source_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        # Determine mime type
        suffix = source_path.suffix.lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
        mime_type = mime_map.get(suffix, "image/jpeg")
        
        # Submit generation task
        task_id = await self._submit_task(
            endpoint=model,
            payload={
                "prompt": prompt,
                "input_image": f"data:{mime_type};base64,{image_data}",
                "strength": strength,
                "width": width,
                "height": height,
                **kwargs,
            }
        )
        
        # Poll for result
        result = await self._poll_result(task_id)
        
        return {
            "task_id": task_id,
            "status": "completed",
            "image_url": result.get("sample"),
            "seed": result.get("seed"),
            "model": model,
            "prompt": prompt,
            "strength": strength,
        }
    
    async def generate_from_asset(
        self,
        asset_id: UUID,
        prompt: str,
        strength: float = 0.75,
        model: str = "flux-kontext-pro",
        **kwargs,
    ) -> dict[str, Any]:
        """
        Generate an image using an existing asset as the source.
        
        Args:
            asset_id: The source asset ID
            prompt: The transformation prompt
            strength: How much to transform
            model: Model to use
            
        Returns:
            dict with generation result and new asset info
        """
        # Get the source asset
        asset = await self.container.asset_service.get(asset_id)
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")
        
        # Download to temp file
        temp_path = await self._download_asset_to_temp(asset)
        
        try:
            # Generate
            result = await self.generate_image_to_image(
                prompt=prompt,
                source_image_path=temp_path,
                strength=strength,
                model=model,
                **kwargs,
            )
            
            # Download the generated image and create a new asset
            if result.get("image_url"):
                new_asset = await self._save_generated_image(
                    image_url=result["image_url"],
                    source_asset_id=asset_id,
                    prompt=prompt,
                    generation_metadata=result,
                )
                result["generated_asset_id"] = str(new_asset.id)
            
            return result
            
        finally:
            # Cleanup temp file
            if temp_path.exists():
                temp_path.unlink()
    
    async def _submit_task(self, endpoint: str, payload: dict) -> str:
        """Submit a generation task to BFL API."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{BFL_API_BASE}/{endpoint}",
                headers={
                    "X-Key": self.api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            
            if response.status_code != 200:
                logger.error("Flux API error", status=response.status_code, body=response.text)
                raise RuntimeError(f"BFL API error: {response.status_code} - {response.text}")
            
            data = response.json()
            task_id = data.get("id")
            
            if not task_id:
                raise RuntimeError(f"No task ID in response: {data}")
            
            logger.info("Flux: Task submitted", task_id=task_id)
            return task_id
    
    async def _poll_result(self, task_id: str, max_attempts: int = 60, interval: float = 2.0) -> dict:
        """Poll for generation result."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(max_attempts):
                response = await client.get(
                    f"{BFL_API_BASE}/get_result",
                    params={"id": task_id},
                    headers={"X-Key": self.api_key},
                )
                
                if response.status_code != 200:
                    logger.warning("Flux: Poll error", status=response.status_code)
                    await asyncio.sleep(interval)
                    continue
                
                data = response.json()
                status = data.get("status")
                
                if status == "Ready":
                    logger.info("Flux: Generation complete", task_id=task_id)
                    return data.get("result", {})
                elif status == "Error":
                    raise RuntimeError(f"Generation failed: {data}")
                elif status in ("Pending", "Processing", "Queued"):
                    logger.debug("Flux: Still processing", status=status, attempt=attempt)
                    await asyncio.sleep(interval)
                else:
                    logger.warning("Flux: Unknown status", status=status)
                    await asyncio.sleep(interval)
            
            raise TimeoutError(f"Generation timed out after {max_attempts * interval}s")
    
    async def _download_asset_to_temp(self, asset) -> Path:
        """Download an asset to a temporary file."""
        import tempfile
        temp_dir = Path(tempfile.mkdtemp())
        temp_path = temp_dir / f"{asset.id}{asset.file_extension}"
        
        async for chunk in self.container.storage.get(asset.storage_path):
            with open(temp_path, "ab") as f:
                f.write(chunk)
        
        return temp_path
    
    async def _save_generated_image(
        self,
        image_url: str,
        source_asset_id: UUID,
        prompt: str,
        generation_metadata: dict,
    ):
        """Download generated image and save as new asset."""
        # Download the image
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(image_url)
            if response.status_code != 200:
                raise RuntimeError(f"Failed to download generated image: {response.status_code}")
            image_data = response.content
        
        # Create new asset
        new_asset = await self.container.ingestion_service.ingest_bytes(
            content=image_data,
            filename=f"flux_generated_{uuid4().hex[:8]}.png",
            asset_type="image",
            extra_metadata={
                "generator": "flux",
                "source_asset_id": str(source_asset_id),
                "prompt": prompt,
                "generation_metadata": generation_metadata,
            },
        )
        
        # Create lineage record
        await self.container.lineage_service.create(
            parent_id=source_asset_id,
            child_id=new_asset.id,
            relationship_type="generated_from",
            metadata={
                "generator": "flux",
                "prompt": prompt,
                "model": generation_metadata.get("model"),
            },
        )
        
        return new_asset