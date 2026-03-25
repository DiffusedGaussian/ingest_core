#!/usr/bin/env python3
"""
Test BFL FLUX.2 API for image editing/transformation.
Uses the correct polling_url from the response.

Run: python test_flux2.py path/to/image.webp
"""

import os
import sys
import asyncio
import base64
import httpx
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BFL_API_BASE = "https://api.bfl.ai/v1"


async def transform_drawing(image_path: str):
    """Transform a technical drawing into a photorealistic render using FLUX.2."""
    api_key = os.getenv("BFL_API_KEY")
    
    print(f"API Key found: {bool(api_key)}")
    if not api_key:
        print("ERROR: BFL_API_KEY not found in .env")
        return None
    
    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    
    # Load image
    path = Path(image_path)
    if not path.exists():
        print(f"ERROR: Image not found: {path}")
        return None
    
    print(f"Loading image: {path.name} ({path.stat().st_size / 1024:.1f} KB)")
    
    with open(path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")
    
    # Prompt for transforming technical drawing to 3D render
    prompt = """Professional e-commerce product photography of this black tote bag, clean white seamless background, soft studio lighting with subtle shadows, crisp detail on fabric texture and zipper hardware, commercial catalog quality, even lighting from all angles, no harsh reflections
    """
    
    print(f"\nPrompt: {prompt[:100]}...")
    print(f"\nSubmitting to flux-2-pro-preview...")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Submit request
        response = await client.post(
            f"{BFL_API_BASE}/flux-2-pro-preview",
            headers={
                "x-key": api_key,
                "Content-Type": "application/json",
            },
            json={
                "prompt": prompt,
                "input_image": image_base64,  # Base64 without data URI prefix
                "width": 1024,
                "height": 1024,
                "output_format": "png",
            },
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error: {response.text}")
            return None
        
        data = response.json()
        task_id = data.get("id")
        polling_url = data.get("polling_url")  # IMPORTANT: Use this URL!
        cost = data.get("cost")
        
        print(f"Task ID: {task_id}")
        print(f"Polling URL: {polling_url}")
        print(f"Cost: {cost} credits")
        
        if not polling_url:
            print("ERROR: No polling_url in response")
            return None
        
        # Poll for result using the polling_url from response
        print("\nPolling for result...")
        for i in range(120):  # Up to 4 minutes
            await asyncio.sleep(2)
            
            result_response = await client.get(
                polling_url,  # Use the polling_url directly!
                headers={"x-key": api_key},
            )
            
            if result_response.status_code != 200:
                print(f"  Poll error: {result_response.status_code} - {result_response.text[:100]}")
                continue
            
            result_data = result_response.json()
            status = result_data.get("status")
            
            if i % 5 == 0:
                print(f"  Attempt {i+1}: {status}")
            
            if status == "Ready":
                image_url = result_data.get("result", {}).get("sample")
                print(f"\n✅ SUCCESS!")
                print(f"Image URL: {image_url}")
                
                # Download and save
                print("Downloading generated image...")
                img_response = await client.get(image_url)
                output_path = f"flux2_output_{path.stem}.png"
                with open(output_path, "wb") as f:
                    f.write(img_response.content)
                print(f"Saved to: {output_path}")
                return output_path
                
            elif status in ("Error", "Failed"):
                error_msg = result_data.get("error") or result_data
                print(f"\n❌ FAILED: {error_msg}")
                return None
        
        print("\nTimeout waiting for result (4 minutes)")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_flux2.py path/to/image.webp")
        print("\nThis will transform a technical drawing into a 3D render using FLUX.2")
        sys.exit(1)
    
    result = asyncio.run(transform_drawing(sys.argv[1]))
    if result:
        print(f"\n🎉 Done! Check {result}")