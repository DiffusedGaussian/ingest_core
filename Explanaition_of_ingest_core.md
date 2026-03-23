# Ingest Core - Technical Architecture Documentation

## Overview
**ingest_core** is a sophisticated media ingestion and AI-powered video prompt generation system built with Python 3.11, FastAPI, and async/await patterns. It analyzes images using Vision Language Models (VLM) and generates optimized text prompts for video generation tools (Flux, Runway, etc.).

---

## Core Architecture

### **Dependency Injection Container Pattern**
- **Location**: `ingest_core/container/container.py`
- Implements lazy-initialized singleton pattern for all dependencies
- Manages lifecycle of storage backends, databases, analyzers, and services
- Supports pluggable analyzers registered at runtime
- Key methods: `startup()`, `shutdown()`, property-based access

### **Async-First Design**
- All I/O operations are async (storage, database, file processing)
- Uses `motor` for async MongoDB, `aiosqlite` for async SQLite
- Async generators for file streaming
- FastAPI for async HTTP handling

---

## Data Models (Pydantic v2)

### **Asset Hierarchy** (`ingest_core/models/`)
```
Asset (base class)
├── ImageAsset (image-specific metadata)
├── VideoAsset (keyframes, transcription)
└── Asset3D (3D model metadata)
```

**Core Asset Fields:**
- `id: UUID` - Primary identifier
- `asset_type: AssetType` - Enum: IMAGE, VIDEO, ASSET_3D
- `status: AssetStatus` - Enum: PENDING, PROCESSING, COMPLETED, FAILED
- `storage_path: str` - Backend-agnostic path
- `extra_metadata: dict[str, Any]` - Extensible analyzer results
- `embedding_id: str | None` - Reference to vector DB

### **Video Prompt Generation Models**
**VideoPromptAnalysis** - Structured image analysis:
- `subject: SubjectInfo` - Main subject description, position, movable elements
- `scene: SceneInfo` - Location, setting type, time of day, weather
- `composition: CompositionInfo` - Foreground, midground, background layers
- `lighting: LightingInfo` - Source, direction, quality, color temperature
- `style: StyleInfo` - Medium, aesthetic, color palette, lens characteristics
- `motion: MotionSuggestions` - Subject/environment motions, camera suggestions
- `shot_type: ShotType` - Enum of cinematographic shot types
- `mood: MoodTone` - Enum of emotional tones

**GeneratedVideoPrompt** - Final output:
- `prompt: str` - Complete prompt text
- `prompt_components: dict[str, str]` - Decomposed parts (subject, camera, environment)
- `recommended_camera: CameraMovement` - Enum: DOLLY_IN, ORBIT_RIGHT, etc.
- `recommended_speed: MovementSpeed` - Enum: VERY_SLOW to VERY_FAST
- `target_generator: str` - Target video generator (flux, runway)

### **Prompt Templates** (`ingest_core/models/prompt_template.py`)
- Predefined templates: default, fashion_editorial, product_hero, cinematic, minimal, lifestyle
- Format string with placeholders: `{subject}`, `{camera}`, `{location}`, etc.
- Default values and required fields
- Composable with VLM-extracted data

---

## Processing Pipeline

### **Ingestion Flow** (`ingest_core/services/ingestion.py`)
```
Upload → Store → Process → Analyze → Index
```

1. **Upload**: File received via FastAPI multipart
2. **Store**: Save to storage backend (local filesystem or GCS)
3. **Process**: 
   - Validate file (format, size limits)
   - Extract metadata (EXIF, dimensions, codec info)
   - Generate thumbnails
4. **Analyze**: Run analyzer plugins
5. **Index**: Store in document DB + vector DB

### **Analyzer System** (Pluggable)
**Base Class**: `ingest_core/analyzers/base.py::BaseAnalyzer`
- Abstract `analyze()` method returning `AnalyzerResult`
- `supports()` method for asset type filtering

**Built-in Analyzers**:
1. **EXIFAnalyzer** - Extract EXIF metadata, GPS coordinates
2. **PerceptualHashAnalyzer** - Generate pHash for duplicate detection
3. **ObjectDetectionAnalyzer** - Detect objects using Gemini VLM
4. **VLMAnalyzer** - Full image description using Gemini or LLaVA

**Registration**: Via `container.register_analyzer(name, instance)`

### **Processor System** (Type-Specific)
**Base Class**: `ingest_core/processors/base.py::BaseProcessor`

**Processors**:
1. **ImageProcessor** - Pillow-based validation, metadata, thumbnails
2. **VideoProcessor** - FFmpeg for metadata, keyframe extraction, Whisper transcription
3. **Asset3DProcessor** - 3D model handling (trimesh/PyMeshLab)

---

## Prompt Generation Workflow

### **Core Service**: `ingest_core/services/prompt_generator.py::PromptGeneratorService`

**Method 1: `analyze_image(asset_id)`**
```python
# Extracts structured data using VLM
1. Download asset to temp file
2. Call Gemini VLM with EXTRACTION_PROMPT (JSON schema)
3. Parse JSON response into VideoPromptAnalysis
4. Save to asset.extra_metadata["video_prompt_analysis"]
```

**EXTRACTION_PROMPT Schema**:
```json
{
  "subject": {"description": "...", "position_in_frame": "...", "movable_elements": []},
  "scene": {"location": "...", "time_of_day": "..."},
  "composition": {"foreground": "...", "background": "..."},
  "lighting": {"primary_source": "...", "quality": "..."},
  "motion_suggestions": {"camera_suggestions": ["dolly_in"], "recommended_speed": "slow"}
}
```

**Method 2: `generate_prompt(asset_id, camera_movement?, movement_speed?, duration)`**
```python
1. Get VideoPromptAnalysis (or create if missing)
2. Compose prompt parts:
   - subject_prompt = f"{subject.description} in {scene.location}"
   - camera_prompt = f"{speed} {camera_movement_text}"
   - environment_prompt = motion + lighting descriptors
3. Combine: f"{subject}. {camera}. {environment}"
4. Save as GeneratedVideoPrompt
```

**Method 3: `generate_prompt_with_template(asset_id, template_id, overrides?)`**
```python
1. Get VideoPromptAnalysis
2. Load PromptTemplate from TEMPLATES dict
3. Build context dict from analysis
4. Apply template.defaults
5. Apply user overrides
6. Format template string: template.template.format(**context)
7. Save GeneratedVideoPrompt
```

---

## Storage Layer

### **Abstract Interface**: `ingest_core/storage/base.py::StorageBackend`
```python
async def save(file_obj, destination, content_type) -> str
async def get(path) -> AsyncGenerator[bytes, None]  # Streaming
async def delete(path) -> bool
async def exists(path) -> bool
def get_url(path) -> str
```

### **Implementations**:
1. **LocalStorage** (`ingest_core/storage/local.py`)
   - File system storage with async file operations
   - Path: `{base_dir}/{destination}`
   
2. **GCSStorage** (`ingest_core/storage/gcs.py`)
   - Google Cloud Storage integration
   - Uses `google-cloud-storage` client
   - Supports presigned URLs

**Factory**: `ingest_core/storage/factory.py::get_storage_backend(settings)`

---

## Database Layer

### **Document Store** (Switchable Backend)
**MongoDB** (`ingest_core/database/mongodb.py`):
- Motor async client
- Collections: `assets`, `lineage`
- Methods: `connect()`, `disconnect()`, `.db.assets.find_one()`

**SQLite** (`ingest_core/database/sqlite.py`):
- aiosqlite async client
- JSON column for metadata
- Methods: `initialize()`, `close()`, custom CRUD

### **Vector Store** (Switchable Backend)
**Qdrant** (`ingest_core/database/qdrant.py`):
- Qdrant client for semantic search
- Methods: `initialize()`, `upsert()`, `search()`

**FAISS** (`ingest_core/database/faiss_db.py`):
- Local vector store using FAISS
- File-based persistence

**Selection**: Via `settings.database_backend` and `settings.vector_database_backend`

---

## API Structure (FastAPI)

### **Entry Point**: `ingest_core/api/app.py`
```python
app = FastAPI(
    title="Ingest Core API",
    lifespan=lifespan_context  # Handles startup/shutdown
)
app.include_router(assets_router)
app.include_router(prompts_router)
app.include_router(analysis_router)
app.include_router(search_router)
app.include_router(lineage_router)
app.include_router(health_router)
```

### **Key Routes** (`ingest_core/api/routes/`)

**assets.py**:
- `POST /api/v1/assets` - Upload file (multipart), returns Asset
- `GET /api/v1/assets` - List assets with pagination
- `GET /api/v1/assets/{id}` - Get asset details
- `DELETE /api/v1/assets/{id}` - Delete asset
- `GET /api/v1/assets/{id}/download` - Stream file download

**prompts.py**:
- `POST /api/v1/assets/{id}/generate-prompt` - Generate default prompt
- `POST /api/v1/assets/{id}/generate-prompt-with-template` - Use template
- `GET /api/v1/assets/{id}/prompt` - Get latest prompt
- `GET /api/v1/prompts/export?format=csv|json` - Bulk export prompts
- `GET /api/v1/templates` - List prompt templates
- `GET /api/v1/templates/{id}` - Get template details

**analysis.py**:
- `POST /api/v1/assets/{id}/analyze` - Run analyzer pipeline

**Dependencies**: `ContainerDep = Depends(get_container)` injected into all routes

---

## Configuration System

### **Settings** (`ingest_core/config/settings.py`)
Pydantic Settings with nested groups:
```python
Settings:
  ├── paths: PathSettings (data_dir, upload_dir, temp_dir)
  ├── storage: StorageSettings (backend, gcs_bucket)
  ├── mongodb: MongoDBSettings (uri, database)
  ├── qdrant: QdrantSettings (host, port, api_key)
  ├── sqlite: SQLiteSettings (path)
  ├── gemini: GeminiSettings (api_key, model)
  ├── local_vlm: LocalVLMSettings (model, device)
  ├── whisper: WhisperSettings (model, device)
  ├── processing: ProcessingSettings (max_file_size_mb, keyframe_max_count)
  ├── api: APISettings (host, port, workers)
  └── plugins: PluginSettings (enabled_analyzers)
```

**Environment Variables**:
- Prefix: `INGEST_` (e.g., `INGEST_DATABASE_BACKEND=mongodb`)
- Gemini-specific: `GEMINI_API_KEY`, `GEMINI_MODEL`
- Loads from `.env` file

---

## Service Layer

### **AssetService** (`ingest_core/services/asset.py`)
- CRUD operations for assets
- Methods: `create()`, `get()`, `update_status()`, `delete()`
- Abstracts database backend

### **IngestionService** (`ingest_core/services/ingestion.py`)
- Orchestrates full ingestion pipeline
- `ingest_file()` - End-to-end upload to processing
- `process_asset()` - Run processors and analyzers

### **LineageService** (`ingest_core/services/lineage.py`)
- Track asset relationships (generation, transformation)
- `record_generation(source_id, target_id)` - Link source → generated asset
- `get_full_lineage(asset_id)` - Traverse ancestor/descendant graph

### **PromptGeneratorService** (Detailed above)
- VLM-powered analysis
- Prompt composition
- Template-based generation

---

## Key Technical Decisions

1. **Async Everywhere**: All I/O is async for scalability
2. **Backend Agnostic**: Swap storage/database via config
3. **Pluggable Analyzers**: Extend functionality without core changes
4. **Structured Extraction**: VLM returns JSON schema, not freeform text
5. **Template System**: Reusable prompt patterns for different use cases
6. **Streaming**: File downloads/uploads use async generators
7. **Dependency Injection**: Container pattern for testability
8. **Type Safety**: Pydantic models for all data structures

---

## Dependencies (Key Libraries)

- **FastAPI** - Async web framework
- **Pydantic v2** - Data validation
- **Motor** - Async MongoDB driver
- **Qdrant-client** - Vector database
- **google-generativeai** - Gemini VLM
- **Pillow** - Image processing
- **opencv-python** - Computer vision
- **ffmpeg-python** - Video processing
- **imagehash** - Perceptual hashing
- **structlog** - Structured logging

---

## Usage Patterns

### **Basic Flow**:
```python
# 1. Upload image
response = POST /api/v1/assets (file=image.jpg)
asset_id = response.id

# 2. Generate prompt
POST /api/v1/assets/{asset_id}/generate-prompt-with-template
{
  "template_id": "cinematic",
  "overrides": {"location": "rainy city street"},
  "duration": 5
}

# 3. Get prompt
GET /api/v1/assets/{asset_id}/prompt
→ {"prompt": "Woman in oversized sweater in rainy city street. Slow push in. Cinematic color grade..."}

# 4. Export all prompts
GET /api/v1/prompts/export?format=csv
```

---

This codebase is designed for **production-grade media ingestion** with AI-powered prompt generation, supporting flexible storage, databases, and extensible analysis pipelines.