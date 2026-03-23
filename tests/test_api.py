"""
Tests for API endpoints.

Tests FastAPI routes and request/response handling.
"""

import io
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ingest_core.api.app import app
from ingest_core.api.schemas import AssetResponse, AssetListResponse


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check returns OK."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestAssetEndpoints:
    """Tests for asset CRUD endpoints."""
    
    @pytest.mark.skip(reason="Requires full container setup with database")
    def test_upload_asset(self, client, sample_image_path):
        """Test uploading an asset."""
        with open(sample_image_path, "rb") as f:
            response = client.post(
                "/api/v1/assets",
                files={"file": ("test.jpg", f, "image/jpeg")},
                data={"auto_analyze": "false"}
            )
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["asset_type"] == "image"
    
    @pytest.mark.skip(reason="Requires full container setup")
    def test_list_assets(self, client):
        """Test listing assets."""
        response = client.get("/api/v1/assets")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
    
    @pytest.mark.skip(reason="Requires full container setup")
    def test_get_asset_by_id(self, client):
        """Test getting single asset."""
        # This would need a real asset ID
        asset_id = uuid4()
        response = client.get(f"/api/v1/assets/{asset_id}")
        
        # Expect 404 for non-existent asset
        assert response.status_code == 404
    
    def test_invalid_upload_no_file(self, client):
        """Test upload without file."""
        response = client.post("/api/v1/assets")
        
        assert response.status_code == 422  # Validation error


class TestAssetResponseSchema:
    """Tests for API response schemas."""
    
    def test_asset_response_schema(self, sample_asset):
        """Test AssetResponse schema validation."""
        response = AssetResponse.model_validate(sample_asset)
        
        assert response.id == sample_asset.id
        assert response.asset_type == sample_asset.asset_type
        assert response.status == sample_asset.status
    
    def test_asset_list_response_schema(self, sample_asset):
        """Test AssetListResponse schema."""
        response = AssetListResponse(
            items=[AssetResponse.model_validate(sample_asset)],
            total=1,
            page=1,
            page_size=20,
            has_more=False
        )
        
        assert len(response.items) == 1
        assert response.total == 1
        assert response.has_more is False


class TestAPIErrorHandling:
    """Tests for API error handling."""
    
    def test_404_not_found(self, client):
        """Test 404 for non-existent routes."""
        response = client.get("/api/v1/nonexistent")
        
        assert response.status_code == 404
    
    def test_method_not_allowed(self, client):
        """Test 405 for wrong HTTP method."""
        # Health check is GET only
        response = client.post("/api/v1/health")
        
        assert response.status_code == 405


class TestAPIDocumentation:
    """Tests for API documentation endpoints."""
    
    def test_openapi_schema(self, client):
        """Test OpenAPI schema is available."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
    
    def test_docs_endpoint(self, client):
        """Test Swagger UI docs endpoint."""
        response = client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_redoc_endpoint(self, client):
        """Test ReDoc endpoint."""
        response = client.get("/redoc")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
