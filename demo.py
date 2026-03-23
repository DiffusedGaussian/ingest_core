#!/usr/bin/env python3
"""
Demo script for ingest-core pipeline.

This shows the full workflow:
1. Start the API server
2. Upload an image
3. Get back a video-ready prompt

Usage:
    # Terminal 1: Start the server
    python demo.py server
    
    # Terminal 2: Run the demo
    python demo.py upload path/to/image.jpg
    
    # Or use curl directly:
    curl -X POST "http://localhost:8001/api/v1/pipeline/upload-and-process" \
        -F "file=@image.jpg" \
        -F "generator=runway"
"""

import argparse
import asyncio
import sys
from pathlib import Path


def start_server(host: str = "0.0.0.0", port: int = 8001):
    """Start the FastAPI server."""
    try:
        import uvicorn
        from ingest_core.api.app import app
        
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    ingest-core API Server                     ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Docs:     http://{host}:{port}/docs                            ║
║  Health:   http://{host}:{port}/health                          ║
║  Pipeline: http://{host}:{port}/api/v1/pipeline                 ║
║                                                              ║
║  Quick test:                                                 ║
║  curl -X POST "http://localhost:{port}/api/v1/pipeline/upload-and-process" \\
║       -F "file=@image.jpg" -F "generator=runway"             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """)
        
        uvicorn.run("ingest_core.api.app:app", host=host, port=port, reload=True)
        
    except ImportError as e:
        print(f"Error: Missing dependency - {e}")
        print("Install with: pip install ingest-core[full]")
        sys.exit(1)


async def upload_image(
    file_path: str,
    server_url: str = "http://localhost:8001",
    generator: str = "runway",
    duration: int = 5,
):
    """Upload an image and get a video prompt."""
    try:
        import httpx
    except ImportError:
        print("Error: httpx not installed. Run: pip install httpx")
        sys.exit(1)
    
    path = Path(file_path)
    if not path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    
    print(f"📤 Uploading: {path.name}")
    print(f"   Generator: {generator}")
    print(f"   Duration: {duration}s")
    print()
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Upload and process
        with open(path, "rb") as f:
            response = await client.post(
                f"{server_url}/api/v1/pipeline/upload-and-process",
                files={"file": (path.name, f, "image/jpeg")},
                data={
                    "generator": generator,
                    "duration": str(duration),
                },
            )
        
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            sys.exit(1)
        
        result = response.json()
        
        print("✅ Pipeline complete!")
        print()
        print(f"   Asset ID: {result['asset_id']}")
        print(f"   Status:   {result['status']}")
        print()
        
        if result.get("prompt"):
            print("📝 Generated Prompt:")
            print("─" * 60)
            print(result["prompt"])
            print("─" * 60)
        
        if result.get("analysis"):
            analysis = result["analysis"]
            print()
            print("🔍 Analysis:")
            if "subject" in analysis:
                print(f"   Subject: {analysis['subject'].get('description', 'N/A')}")
            if "scene" in analysis:
                print(f"   Scene:   {analysis['scene'].get('location', 'N/A')}")
            if "mood" in analysis:
                print(f"   Mood:    {analysis['mood']}")
        
        if result.get("errors"):
            print()
            print("⚠️  Warnings:")
            for error in result["errors"]:
                print(f"   - {error}")
        
        print()
        print("📋 Full response saved to: pipeline_result.json")
        
        import json
        with open("pipeline_result.json", "w") as f:
            json.dump(result, f, indent=2, default=str)


async def check_status(asset_id: str, server_url: str = "http://localhost:8000"):
    """Check pipeline status for an asset."""
    try:
        import httpx
    except ImportError:
        print("Error: httpx not installed")
        sys.exit(1)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{server_url}/api/v1/pipeline/status/{asset_id}"
        )
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)
            sys.exit(1)
        
        result = response.json()
        
        print(f"Asset: {result['asset_id']}")
        print(f"Has Analysis: {result['has_analysis']}")
        print(f"Has Prompt: {result['has_prompt']}")
        
        if result.get("prompt"):
            print()
            print("Prompt:")
            print(result["prompt"])


async def list_templates(server_url: str = "http://localhost:8000"):
    """List available prompt templates."""
    try:
        import httpx
    except ImportError:
        print("Error: httpx not installed")
        sys.exit(1)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{server_url}/api/v1/pipeline/templates")
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            sys.exit(1)
        
        result = response.json()
        
        print("Available Templates:")
        print()
        for t in result.get("templates", []):
            print(f"  {t['id']}: {t['name']}")
            print(f"    {t['description']}")
            print()


def main():
    parser = argparse.ArgumentParser(
        description="ingest-core pipeline demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python demo.py server                    # Start the API server
  python demo.py upload image.jpg          # Upload and process an image
  python demo.py upload image.jpg --generator kling --duration 10
  python demo.py status <asset-id>         # Check status
  python demo.py templates                 # List prompt templates
        """,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Server command
    server_parser = subparsers.add_parser("server", help="Start API server")
    server_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    server_parser.add_argument("--port", type=int, default=8001, help="Port to listen on")
    
    # Upload command
    upload_parser = subparsers.add_parser("upload", help="Upload and process an image")
    upload_parser.add_argument("file", help="Path to image file")
    upload_parser.add_argument("--server", default="http://localhost:8001", help="Server URL")
    upload_parser.add_argument("--generator", default="runway", help="Target generator")
    upload_parser.add_argument("--duration", type=int, default=5, help="Video duration")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check asset status")
    status_parser.add_argument("asset_id", help="Asset ID to check")
    status_parser.add_argument("--server", default="http://localhost:8001", help="Server URL")
    
    # Templates command
    templates_parser = subparsers.add_parser("templates", help="List prompt templates")
    templates_parser.add_argument("--server", default="http://localhost:8001", help="Server URL")
    
    args = parser.parse_args()
    
    if args.command == "server":
        start_server(args.host, args.port)
    elif args.command == "upload":
        asyncio.run(upload_image(args.file, args.server, args.generator, args.duration))
    elif args.command == "status":
        asyncio.run(check_status(args.asset_id, args.server))
    elif args.command == "templates":
        asyncio.run(list_templates(args.server))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
