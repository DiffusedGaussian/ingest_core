# Ingest Core

A robust, extensible media ingestion and analysis framework.

## Overview

Ingest Core is a specialized engine designed to handle various media types (images, videos, 3D assets) through a pipeline of processing, analysis, and storage. It provides an abstract framework for plugging in different analyzers (EXIF, Phash, Object Detection, VLM) and supports multiple storage and database backends.

## Features

- **Extensible Analyzer Architecture**: Easily add new analysis capabilities.
- **Multi-Media Support**: Handle images, videos, and 3D files.
- **Flexible Storage**: Local filesystem and Google Cloud Storage (GCS) support.
- **Database Options**: MongoDB for metadata, SQLite for local development, and Qdrant for vector embeddings.
- **Async First**: Built on Python's `asyncio` for high-concurrency performance.

## Project Structure

```text
ingest_core/
├── analyzer/         # Analysis logic (EXIF, phash, VLM, etc.)
├── api/              # API layer for interaction
├── config/           # Application configuration
├── container/        # Dependency injection container
├── database/         # Database adapters (MongoDB, SQLite, Qdrant)
├── models/           # Pydantic data models
├── processor/        # Media processing logic
├── service/          # Business logic and orchestration
└── storage/          # Storage backends (Local, GCS)
```

## Getting Started

### Prerequisites

- Python 3.10+
- (Optional) Docker for running databases like MongoDB/Qdrant

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd ingest_core
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -e .
   ```

### Configuration

Copy the example environment file and adjust your settings:
```bash
cp .env.example .env
```

## Development

### Code Quality

We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting.

To check for issues:
```bash
ruff check .
```

To automatically fix issues:
```bash
ruff check . --fix
```

## License

See the LICENSE file for details.
