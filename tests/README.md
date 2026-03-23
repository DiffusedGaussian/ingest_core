# Tests for Ingest Core

Comprehensive test suite for the ingest_core project covering all major modules and functionality.

## 🏗️ Test Structure

```
tests/
├── conftest.py              # Shared fixtures and pytest configuration
├── test_models.py           # Tests for data models (Asset, StructuredPrompt, etc.)
├── test_adapters.py         # Tests for model adapters (Kling, Runway, etc.)
├── test_processors.py       # Tests for media processors (image, video, 3D)
├── test_storage.py          # Tests for storage backends (local, GCS)
├── test_analyzers.py        # Tests for analyzers (EXIF, phash, VLM)
├── test_config.py           # Tests for configuration and settings
├── test_api.py              # Tests for API endpoints
├── test_services.py         # Tests for service layer
├── test_integration.py      # Integration tests
└── utils.py                 # Test utilities and helpers
```

## 🚀 Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/test_models.py
```

### Run Specific Test Class
```bash
pytest tests/test_models.py::TestAssetModel
```

### Run Specific Test
```bash
pytest tests/test_models.py::TestAssetModel::test_create_asset
```

### Run Tests by Marker
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

## 📊 Coverage Reports

### Generate Coverage Report
```bash
pytest --cov=ingest_core --cov-report=html
```

View the HTML report by opening `htmlcov/index.html` in your browser.

### Coverage Terminal Report
```bash
pytest --cov=ingest_core --cov-report=term-missing
```

## 🏷️ Test Markers

Tests are categorized using markers:

- `@pytest.mark.unit` - Fast unit tests with no external dependencies
- `@pytest.mark.integration` - Integration tests requiring database/storage
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.requires_api_key` - Tests requiring external API keys (Gemini, etc.)
- `@pytest.mark.requires_db` - Tests requiring database connection
- `@pytest.mark.requires_gpu` - Tests requiring GPU/CUDA

Example:
```python
@pytest.mark.unit
def test_asset_creation():
    """Fast unit test."""
    pass

@pytest.mark.integration
@pytest.mark.requires_db
async def test_database_operations():
    """Integration test requiring database."""
    pass
```

## 🔧 Fixtures

Common fixtures are defined in `conftest.py`:

- `test_settings` - Isolated test settings with temporary directories
- `sample_asset` - Sample Asset model instance
- `sample_image_path` - Generated test image file
- `sample_structured_prompt` - Sample StructuredPrompt instance
- `empty_structured_prompt` - Empty StructuredPrompt with defaults
- `sample_vlm_response` - Mock VLM analysis response
- `sample_exif_data` - Mock EXIF metadata

## 📝 Writing Tests

### Test Naming Convention
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Example Test
```python
import pytest
from ingest_core.models.asset import Asset, AssetType

class TestAssetModel:
    """Tests for Asset model."""
    
    def test_create_asset(self):
        """Test creating a basic asset."""
        asset = Asset(
            asset_type=AssetType.IMAGE,
            original_filename="test.jpg",
            file_extension=".jpg",
            file_size_bytes=1024,
            mime_type="image/jpeg",
            storage_path="assets/test.jpg",
        )
        
        assert asset.id is not None
        assert asset.asset_type == AssetType.IMAGE
```

### Async Test Example
```python
@pytest.mark.asyncio
async def test_async_operation(processor, sample_image_path):
    """Test async processor operation."""
    result = await processor.validate(sample_image_path)
    assert result[0] is True
```

## 🔍 Test Categories

### Unit Tests
Fast tests that don't require external dependencies:
- Model validation and serialization
- Utility functions
- Configuration parsing
- Adapter compilation logic

### Integration Tests
Tests that require external resources:
- Database operations
- Storage backend operations
- API endpoint tests
- Full ingestion pipeline tests

Some integration tests are skipped by default if dependencies aren't available.

## 🐛 Debugging Tests

### Run Tests with Verbose Output
```bash
pytest -vv
```

### Show Print Statements
```bash
pytest -s
```

### Drop into PDB on Failure
```bash
pytest --pdb
```

### Run Last Failed Tests
```bash
pytest --lf
```

### Run Tests in Parallel
```bash
pytest -n auto
```

## 📈 CI/CD Integration

Tests are designed to run in CI/CD pipelines. Example GitHub Actions workflow:

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov pytest-asyncio
      - run: pytest --cov=ingest_core
```

## 🔐 Environment Variables for Tests

Some tests may require environment variables:

```bash
# For VLM tests
export GEMINI_API_KEY=your_test_key

# For database tests
export INGEST_DATABASE_BACKEND=sqlite
export INGEST_VECTOR_DATABASE_BACKEND=local
```

## 📦 Test Dependencies

Install test dependencies:

```bash
pip install pytest pytest-asyncio pytest-cov
```

Or with development dependencies:

```bash
pip install -e ".[dev]"
```

## 🎯 Coverage Goals

Target coverage goals:
- Overall: >80%
- Critical modules (models, adapters, processors): >90%
- API endpoints: >85%
- Services: >80%

## 🤝 Contributing Tests

When adding new features:

1. Write tests first (TDD approach recommended)
2. Ensure tests cover happy path and edge cases
3. Add appropriate markers
4. Update this README if adding new test categories
5. Maintain or improve coverage percentage

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Pytest Markers](https://docs.pytest.org/en/stable/mark.html)
- [Coverage.py](https://coverage.readthedocs.io/)
