# Ingest Core 🎨

A robust media ingestion and AI-powered prompt generation system. Analyze images, generate optimized video prompts, and export data for video generation workflows.

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/DiffusedGaussian/ingest_core.git
cd ingest_core

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install google-generativeai  # For Gemini VLM
```

### 2. Configuration

```bash
# Create .env file
cat > .env << EOF
# Gemini API Key (required for VLM analysis)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3-flash-preview

# Database (defaults to SQLite for local dev)
INGEST_DATABASE_BACKEND=sqlite
INGEST_VECTOR_DATABASE_BACKEND=local

# Storage (defaults to local filesystem)
INGEST_STORAGE_BACKEND=local
EOF
```

### 3. Start the Server

```bash
uvicorn ingest_core.api:app --reload --port 8001
```

Server will be running at: **http://localhost:8001**
- API Docs: http://localhost:8001/docs
- Interactive API: http://localhost:8001/redoc

---

## 📖 Complete Usage Guide

### Upload & Analyze Images

#### Upload an Image
```bash
curl -X POST http://localhost:8001/api/v1/assets \
  -F "file=@/path/to/your/image.jpg" \
  -F "auto_analyze=true"
```

**Response:**
```json
{
  "id": "42e48987-8aa3-4772-ab3e-a357e61ebfb1",
  "asset_type": "image",
  "status": "completed",
  "original_filename": "fashion_photo.jpg",
  "created_at": "2026-03-04T14:05:14.049963"
}
```

---

### Generate Video Prompts

#### 1. Generate Default Prompt
```bash
curl -X POST http://localhost:8001/api/v1/assets/42e48987-8aa3-4772-ab3e-a357e61ebfb1/generate-prompt \
  -H "Content-Type: application/json" \
  -d '{
    "duration": 5,
    "target_generator": "flux"
  }'
```

**Response:**
```json
{
  "asset_id": "42e48987-8aa3-4772-ab3e-a357e61ebfb1",
  "prompt": "Young woman wearing oversized mauve sweater in studio setting. Slow camera pushes in toward subject. Soft lighting",
  "recommended_camera": "dolly_in",
  "recommended_speed": "slow",
  "recommended_duration": 5
}
```

#### 2. Generate with Custom Camera Movement
```bash
curl -X POST http://localhost:8001/api/v1/assets/42e48987-8aa3-4772-ab3e-a357e61ebfb1/generate-prompt \
  -H "Content-Type: application/json" \
  -d '{
    "camera_movement": "orbit_right",
    "movement_speed": "moderate",
    "duration": 8
  }'
```

---

### 🎬 Prompt Templates

#### List Available Templates
```bash
curl http://localhost:8001/api/v1/templates
```

**Available Templates:**
- `default` - Basic prompt structure
- `fashion_editorial` - High fashion aesthetic with editorial lighting
- `product_hero` - Clean product showcase
- `cinematic` - Film-like dramatic style with color grading
- `minimal` - Simple, clean aesthetic
- `lifestyle` - Natural lifestyle photography

#### Get Template Details
```bash
curl http://localhost:8001/api/v1/templates/fashion_editorial
```

**Response:**
```json
{
  "id": "fashion_editorial",
  "name": "Fashion Editorial",
  "description": "High fashion editorial style with emphasis on clothing and styling",
  "template": "{subject}, {clothing}. {camera}. {motion}. Soft editorial lighting, high fashion aesthetic.",
  "defaults": {
    "camera": "Slow dolly in",
    "motion": "hair gently moving",
    "clothing": "wearing fashionable attire"
  }
}
```

#### Generate Prompt with Template
```bash
curl -X POST http://localhost:8001/api/v1/assets/42e48987-8aa3-4772-ab3e-a357e61ebfb1/generate-prompt-with-template \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "cinematic",
    "overrides": {
      "location": "neon-lit city street at night",
      "motion": "rain falling, reflections on wet pavement"
    },
    "duration": 10
  }'
```

**Response:**
```json
{
  "prompt": "Young woman wearing oversized sweater in neon-lit city street at night. Slow push in. Rain falling, reflections on wet pavement. Cinematic color grade, film grain, anamorphic lens.",
  "prompt_components": {
    "subject": "Young woman wearing oversized sweater",
    "location": "neon-lit city street at night",
    "motion": "rain falling, reflections on wet pavement"
  }
}
```

---

### 📊 Export Prompts

#### Export as JSON
```bash
curl http://localhost:8001/api/v1/prompts/export
```

**Response:**
```json
{
  "prompts": [
    {
      "asset_id": "42e48987-8aa3-4772-ab3e-a357e61ebfb1",
      "filename": "fashion_photo.jpg",
      "prompt": "Young woman wearing oversized mauve sweater...",
      "camera": "dolly_in",
      "speed": "slow",
      "duration": 5,
      "generator": "flux"
    }
  ],
  "count": 1
}
```

#### Export as CSV
```bash
curl http://localhost:8001/api/v1/prompts/export?format=csv > prompts.csv

# Or with limit
curl "http://localhost:8001/api/v1/prompts/export?format=csv&limit=100" > prompts.csv
```

**CSV Output:**
```csv
asset_id,filename,prompt,camera,speed,duration,generator
42e48987-...,fashion_photo.jpg,"Young woman wearing...",dolly_in,slow,5,flux
```

---

## 🔄 Complete Workflow Example

### Fashion Product Photography → Video

```bash
# 1. Upload fashion image
ASSET_ID=$(curl -X POST http://localhost:8001/api/v1/assets \
  -F "file=@fashion_sweater.jpg" \
  | jq -r '.id')

echo "Uploaded asset: $ASSET_ID"

# 2. Generate prompt with fashion template
curl -X POST "http://localhost:8001/api/v1/assets/$ASSET_ID/generate-prompt-with-template" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "fashion_editorial",
    "overrides": {
      "motion": "hair blowing gently, fabric flowing"
    },
    "duration": 5
  }' | jq '.prompt'

# 3. Get the latest prompt
PROMPT=$(curl "http://localhost:8001/api/v1/assets/$ASSET_ID/prompt" | jq -r '.prompt')

echo "Generated prompt: $PROMPT"

# 4. Use prompt with your video generator (Flux, Runway, etc.)
# Copy the prompt and use it in your preferred video generation tool
```

### Batch Processing Multiple Images

```bash
#!/bin/bash
# Process all images in a directory

for image in ./images/*.jpg; do
  echo "Processing: $image"
  
  # Upload
  ASSET_ID=$(curl -s -X POST http://localhost:8001/api/v1/assets \
    -F "file=@$image" \
    | jq -r '.id')
  
  # Generate cinematic prompt
  curl -s -X POST "http://localhost:8001/api/v1/assets/$ASSET_ID/generate-prompt-with-template" \
    -H "Content-Type: application/json" \
    -d '{
      "template_id": "cinematic",
      "duration": 5
    }' | jq -r '.prompt'
  
  echo "---"
done

# Export all prompts
curl "http://localhost:8001/api/v1/prompts/export?format=csv" > batch_prompts.csv
echo "Exported to batch_prompts.csv"
```

---

## 🎯 Common Use Cases

### 1. E-commerce Product Videos
```bash
curl -X POST "http://localhost:8001/api/v1/assets/$ASSET_ID/generate-prompt-with-template" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "product_hero",
    "overrides": {
      "background": "seamless white studio backdrop"
    }
  }'
```

### 2. Social Media Content
```bash
curl -X POST "http://localhost:8001/api/v1/assets/$ASSET_ID/generate-prompt-with-template" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "lifestyle",
    "overrides": {
      "lighting": "golden hour natural lighting",
      "location": "beach at sunset"
    }
  }'
```

### 3. Artistic/Cinematic Videos
```bash
curl -X POST "http://localhost:8001/api/v1/assets/$ASSET_ID/generate-prompt-with-template" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "cinematic",
    "overrides": {
      "motion": "smoke swirling, dramatic shadows",
      "camera": "Slow crane up revealing scene"
    }
  }'
```

---

## ⚙️ Configuration Reference

### Environment Variables

```bash
# Gemini AI Configuration
GEMINI_API_KEY=your_api_key          # Required for VLM analysis
GEMINI_MODEL=gemini-3-flash-preview  # Or gemini-1.5-flash, gemini-pro

# Database Backend
INGEST_DATABASE_BACKEND=sqlite       # sqlite or mongodb
INGEST_MONGODB_URI=mongodb://localhost:27017  # If using MongoDB

# Vector Database
INGEST_VECTOR_DATABASE_BACKEND=local  # local (FAISS) or qdrant
INGEST_QDRANT_HOST=localhost
INGEST_QDRANT_PORT=6333

# Storage Backend
INGEST_STORAGE_BACKEND=local          # local or gcs
INGEST_GCS_BUCKET=my-bucket          # If using GCS
INGEST_GCS_PROJECT_ID=my-project

# API Configuration
INGEST_API_HOST=0.0.0.0
INGEST_API_PORT=8001
INGEST_API_RELOAD=true               # Auto-reload on code changes

# Data Directories
INGEST_DATA_DIR=./data
INGEST_UPLOAD_DIR=./data/uploads
INGEST_PROCESSED_DIR=./data/processed
```

---

## 🛠️ Development

### Run Tests
```bash
pytest tests/
```

### Code Quality
```bash
# Lint and format
ruff check .
ruff format .
```

### Run with Docker
```bash
docker-compose up -d
```

---

## 📚 API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/assets` | Upload and analyze image |
| `GET` | `/api/v1/assets` | List all assets |
| `GET` | `/api/v1/assets/{id}` | Get asset details |
| `POST` | `/api/v1/assets/{id}/generate-prompt` | Generate default prompt |
| `POST` | `/api/v1/assets/{id}/generate-prompt-with-template` | Generate with template |
| `GET` | `/api/v1/assets/{id}/prompt` | Get latest prompt |
| `GET` | `/api/v1/templates` | List prompt templates |
| `GET` | `/api/v1/templates/{id}` | Get template details |
| `GET` | `/api/v1/prompts/export` | Export all prompts (JSON/CSV) |

### Camera Movements
- `dolly_in` - Push toward subject
- `dolly_out` - Pull away from subject
- `orbit_left` / `orbit_right` - Circle around subject
- `pan_left` / `pan_right` - Horizontal pan
- `crane_up` - Rise upward
- `static` - No movement

### Movement Speeds
- `very_slow` - Subtle, almost imperceptible
- `slow` - Smooth and cinematic
- `moderate` - Steady, noticeable movement
- `fast` - Dynamic, energetic

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🆘 Troubleshooting

### "No module named 'google.generativeai'"
```bash
pip install google-generativeai
```

### "VLM extraction failed"
Check that your `GEMINI_API_KEY` is set correctly in `.env`:
```bash
cat .env | grep GEMINI_API_KEY
```

### "Asset not found"
Make sure you're using the correct asset ID from the upload response.

### Port already in use
Change the port:
```bash
uvicorn ingest_core.api:app --reload --port 8002
```

---

## 📞 Support

- Issues: [GitHub Issues](https://github.com/DiffusedGaussian/ingest_core/issues)
- Documentation: [API Docs](http://localhost:8001/docs)

---

**Built with ❤️ for creative workflows**
