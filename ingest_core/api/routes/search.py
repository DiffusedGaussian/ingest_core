"""
Search endpoints.

Handles text search, similarity search, and filtering.
"""

from fastapi import APIRouter, HTTPException, status

from ingest_core.api.dependencies import ContainerDep
from ingest_core.api.schemas import AssetResponse, SearchRequest, SearchResponse
from ingest_core.models import Asset

router = APIRouter(tags=["search"])


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search assets",
)
async def search_assets(
    request: SearchRequest,
    container: ContainerDep,
) -> SearchResponse:
    """
    Search assets using multiple strategies.

    Strategies:
    - **Text search**: Search in descriptions, tags, filenames
    - **Similarity search**: Find visually similar assets (requires embeddings)
    - **Filters only**: Filter by type, status, date range

    Filters can be combined with any strategy.
    """
    results = []
    total = 0
    search_strategy = "filter"

    # Similarity search
    if request.similar_to:
        search_strategy = "similarity"

        # Get source asset embedding
        source = await container.asset_service.get(request.similar_to)
        if not source or not source.embedding_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source asset has no embedding. Run analysis first.",
            )

        # TODO: Implement when embeddings are generated
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Similarity search not yet implemented. Pending embedding generation.",
        )

    # Text search
    elif request.query:
        search_strategy = "text"

        db = container.db
        if container.settings.database_backend == "mongodb":
            # MongoDB text search (requires text index)
            query = {"$text": {"$search": request.query}}

            # Add filters
            if request.asset_types:
                query["asset_type"] = {"$in": [t.value for t in request.asset_types]}
            if request.status:
                query["status"] = request.status.value

            skip = (request.page - 1) * request.page_size
            cursor = db.assets.find(query).skip(skip).limit(request.page_size)

            items = []
            async for doc in cursor:
                asset = Asset.model_validate(doc)
                items.append({
                    "asset": AssetResponse.model_validate(asset).model_dump(),
                    "score": doc.get("score", 1.0),
                })

            total = await db.assets.count_documents(query)
        else:
            # SQLite FTS
            assets, total = await db.text_search(
                query=request.query,
                filters={
                    "asset_types": request.asset_types,
                    "status": request.status,
                },
                skip=(request.page - 1) * request.page_size,
                limit=request.page_size,
            )
            items = [
                {"asset": AssetResponse.model_validate(a).model_dump(), "score": 1.0}
                for a in assets
            ]

        results = items

    # Filter only (no search query)
    else:
        search_strategy = "filter"

        query = {}
        if request.asset_types:
            if container.settings.database_backend == "mongodb":
                query["asset_type"] = {"$in": [t.value for t in request.asset_types]}
            else:
                query["asset_types"] = request.asset_types
        if request.status:
            if container.settings.database_backend == "mongodb":
                query["status"] = request.status.value
            else:
                query["status"] = request.status
        if request.created_after:
            if container.settings.database_backend == "mongodb":
                query["created_at"] = {"$gte": request.created_after.isoformat()}
            else:
                query["created_after"] = request.created_after
        if request.created_before:
            if container.settings.database_backend == "mongodb":
                query.setdefault("created_at", {})["$lte"] = request.created_before.isoformat()
            else:
                query["created_before"] = request.created_before

        skip = (request.page - 1) * request.page_size

        db = container.db
        if container.settings.database_backend == "mongodb":
            cursor = db.assets.find(query).skip(skip).limit(request.page_size)
            items = [
                {"asset": AssetResponse.model_validate(Asset.model_validate(doc)).model_dump(), "score": 1.0}
                async for doc in cursor
            ]
            total = await db.assets.count_documents(query)
        else:
            assets, total = await db.list_assets(query=query, skip=skip, limit=request.page_size)
            items = [
                {"asset": AssetResponse.model_validate(a).model_dump(), "score": 1.0}
                for a in assets
            ]

        results = items

    return SearchResponse(
        items=results,
        total=total,
        page=request.page,
        page_size=request.page_size,
        search_strategy=search_strategy,
    )