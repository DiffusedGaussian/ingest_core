import asyncio
import os
import sys
from pathlib import Path
import mimetypes

# Add the project root to sys.path
sys.path.append(os.getcwd())

from container.container import Container
from config.settings import get_settings

async def test_ingestion():
    # 1. Initialize settings and container
    settings = get_settings()
    
    # Force local backends for testing
    settings.database_backend = "sqlite"
    settings.vector_database_backend = "local"
    
    container = Container(settings)
    
    print(f"--- Testing Ingestion with {settings.database_backend} DB and {settings.vector_database_backend} Vector backend ---")
    
    # 2. Startup container (initializes DB connections)
    await container.startup()
    
    try:
        # 3. Find the test file
        test_file_path = Path("data/Sometimes-Sweater_CSW_Mellow-Mauve_18.jpg")
        if not test_file_path.exists():
            print(f"Error: Test file {test_file_path} not found.")
            return

        print(f"Ingesting file: {test_file_path.name}")
        
        # 4. Get ingestion service
        service = container.ingestion_service

        # 5. Perform ingestion
        with open(test_file_path, "rb") as f:
            mime_type, _ = mimetypes.guess_type(str(test_file_path))
            asset = await service.ingest_file(
                file_obj=f,
                filename=test_file_path.name,
                content_type=mime_type or "image/jpeg"
            )
            
        print(f"Successfully ingested asset!")
        print(f"ID: {asset.id}")
        print(f"Status: {asset.status}")
        print(f"Type: {asset.asset_type}")
        print(f"Metadata: {asset.extra_metadata}")

    except Exception as e:
        print(f"Ingestion failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 6. Shutdown
        await container.shutdown()

if __name__ == "__main__":
    asyncio.run(test_ingestion())
