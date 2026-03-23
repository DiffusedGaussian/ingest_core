# Testing Guide for Ingest Core

This document provides an overview of the comprehensive testing infrastructure added to the ingest_core project.

## 📋 Overview

A complete testing suite has been added covering:
- **Unit tests** for all core modules
- **Integration tests** for complex workflows
- **API endpoint tests** with FastAPI TestClient
- **Fixtures and utilities** for easy test writing
- **Coverage reporting** with pytest-cov

## 🗂️ Test Structure

```
tests/
├── conftest.py              # Shared pytest fixtures
├── __init__.py             # Package marker
├── test_models.py          # Data model tests (Asset, StructuredPrompt)
├── test_adapters.py        # Model adapter tests (Kling, Runway)
├── test_processors.py      # Media processor tests
├── test_storage.py         # Storage backend tests
├── test_analyzers.py       # Analyzer tests (EXIF, phash)
├── test_config.py          # Configuration/settings tests
├── test_api.py             # API endpoint tests
├── test_services.py        # Service layer tests
├── test_integration.py     # End-to-end integration tests
├── utils.py                # Test utility functions
└── README.md               # Detailed testing documentation
```

## 🚀 Quick Start

### Install Test Dependencies

```bash
# Install pytest and related tools
pip install pytest pytest-asyncio pytest-cov

# Or install all dev dependencies
pip install -e ".[dev]"
```

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=ingest_core --cov-report=html
```

View coverage report: `open htmlcov/index.html`

### Run Specific Test Categories

```bash
# Run only unit tests (fast)
pytest -m unit

# Run integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

## 📊 Test Coverage

The test suite provides comprehensive coverage of:

### Models (test_models.py)
- ✅ Asset model creation and validation
- ✅ Asset status transitions (PENDING → PROCESSING → COMPLETED/FAILED)
- ✅ StructuredPrompt model
- ✅ Category system with overrides
- ✅ Prompt cloning for A/B testing

### Adapters (test_adapters.py)
- ✅ Kling adapter initialization and configuration
- ✅ Prompt compilation with category ordering
- ✅ Camera and lighting vocabulary mapping
- ✅ Negative prompt generation
- ✅ Prompt validation and length checking

### Processors (test_processors.py)
- ✅ Image processor validation
- ✅ Metadata extraction (dimensions, format, EXIF)
- ✅ Thumbnail generation with aspect ratio preservation
- ✅ File format support detection
- ✅ Error handling for invalid files

### Storage (test_storage.py)
- ✅ Local storage save/retrieve operations
- ✅ File existence checking
- ✅ File deletion
- ✅ URL generation
- ✅ Nested directory creation

### Configuration (test_config.py)
- ✅ Settings initialization and validation
- ✅ Environment detection (dev/prod)
- ✅ Path settings with absolute path resolution
- ✅ Adapter configuration (Kling, Runway, Midjourney)
- ✅ Plugin system configuration

### API (test_api.py)
- ✅ Health check endpoint
- ✅ Asset upload validation
- ✅ Response schema validation
- ✅ Error handling (404, 405)
- ✅ OpenAPI documentation endpoints

### Services (test_services.py)
- ✅ Asset type detection from MIME types
- ✅ Prompt compilation with adapters
- ✅ Service layer integration points

### Analyzers (test_analyzers.py)
- ✅ EXIF metadata extraction
- ✅ Perceptual hash computation
- ✅ Analyzer registry and plugin system

### Integration (test_integration.py)
- ✅ Smoke tests for module imports
- ✅ End-to-end workflow stubs (ready for implementation)
- ✅ Performance test structure

## 🔧 Test Fixtures

Common fixtures available in all tests (defined in `conftest.py`):

```python
test_settings         # Isolated test settings with temp directories
sample_asset          # Pre-configured Asset instance
sample_image_path     # Generated test image file
sample_structured_prompt  # Complete StructuredPrompt
empty_structured_prompt   # Empty prompt with defaults
sample_vlm_response   # Mock VLM analysis response
sample_exif_data      # Mock EXIF metadata
```

### Using Fixtures

```python
def test_example(sample_asset, test_settings):
    """Test using fixtures."""
    assert sample_asset.status == AssetStatus.PENDING
    assert test_settings.env == "development"
```

## 🏷️ Test Markers

Categorize tests with markers:

```python
@pytest.mark.unit
def test_fast_unit():
    """Fast test with no dependencies."""
    pass

@pytest.mark.integration
@pytest.mark.requires_db
async def test_database():
    """Integration test requiring database."""
    pass

@pytest.mark.slow
def test_performance():
    """Long-running test."""
    pass
```

Run specific categories:
```bash
pytest -m unit              # Only unit tests
pytest -m "not slow"        # Skip slow tests
pytest -m integration       # Only integration tests
```

## 📝 Writing New Tests

### Test Structure

```python
"""
Module docstring explaining what is tested.
"""

import pytest
from ingest_core.models.asset import Asset

class TestAssetOperations:
    """Group related tests in a class."""
    
    def test_basic_operation(self):
        """Test description."""
        # Arrange
        asset = Asset(...)
        
        # Act
        result = asset.mark_completed()
        
        # Assert
        assert asset.status == AssetStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_async_operation(self, sample_asset):
        """Test async function."""
        result = await process_asset(sample_asset)
        assert result is not None
```

### Best Practices

1. **One assertion concept per test** - Test one thing at a time
2. **Use descriptive names** - `test_asset_status_transitions_to_completed`
3. **Use fixtures** - Don't repeat setup code
4. **Mark appropriately** - Use @pytest.mark for categorization
5. **Test edge cases** - Not just the happy path
6. **Mock external dependencies** - Don't rely on external APIs in unit tests

## 🔍 Debugging Tests

```bash
# Verbose output
pytest -vv

# Show print statements
pytest -s

# Stop on first failure
pytest -x

# Drop into debugger on failure
pytest --pdb

# Run last failed tests only
pytest --lf

# Run specific test with full traceback
pytest tests/test_models.py::test_name -vv --tb=long
```

## 📈 Continuous Integration

The test suite is CI/CD ready. Example GitHub Actions:

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
      - run: pytest --cov=ingest_core --cov-report=xml
      - uses: codecov/codecov-action@v3
```

## 🎯 Coverage Goals

Target test coverage:
- **Overall**: >80%
- **Models**: >90%
- **Adapters**: >90%
- **Processors**: >85%
- **API**: >85%
- **Services**: >80%

Check current coverage:
```bash
pytest --cov=ingest_core --cov-report=term-missing
```

## 🛠️ Test Utilities

Helper functions in `tests/utils.py`:

```python
from tests.utils import (
    create_test_image,          # Create PIL Image
    save_test_image,            # Create and save image file
    create_test_asset,          # Create Asset instance
    create_test_structured_prompt,  # Create StructuredPrompt
    assert_valid_uuid,          # Validate UUID strings
    mock_file_upload,           # Mock upload file object
    create_mock_vlm_response,   # Mock VLM response
)
```

## 📚 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)

## 🤝 Contributing

When adding new features:

1. **Write tests first** (TDD approach)
2. **Ensure all tests pass** before committing
3. **Maintain coverage** - Don't decrease coverage percentage
4. **Add integration tests** for complex workflows
5. **Document test fixtures** if adding new ones

## 📞 Support

For questions about testing:
- Check `tests/README.md` for detailed documentation
- Review existing tests for examples
- Refer to pytest documentation

---

**Test Suite Version**: 1.0  
**Last Updated**: March 2026  
**Python Version**: 3.11+
