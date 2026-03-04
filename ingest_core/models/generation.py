"""
Generation job models.

Tracks generation attempts with full metadata:
- What was requested (prompt, params)
- What generator was used
- Timing (started, completed, duration)
- Status (pending, running, completed, failed)
- Quality metrics (scores, feedback)
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Generation job status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GeneratorType(str, Enum):
    """Known generator types."""

    # Image generators
    FLUX_PRO = "flux-pro"
    FLUX_DEV = "flux-dev"
    FLUX_SCHNELL = "flux-schnell"
    MIDJOURNEY = "midjourney"
    STABLE_DIFFUSION = "stable-diffusion"
    DALLE = "dalle"

    # Video generators
    RUNWAY_GEN3 = "runway-gen3"
    KLING = "kling"
    PIKA = "pika"
    SORA = "sora"
    LUMA = "luma"

    # 3D generators
    MESHY = "meshy"
    TRIPO = "tripo"
    RODIN = "rodin"

    # Custom/other
    CUSTOM = "custom"


class GenerationJob(BaseModel):
    """A single generation attempt."""

    id: UUID = Field(default_factory=uuid4)

    # Generator info
    generator: GeneratorType | str
    generator_version: str | None = None

    # Inputs
    input_asset_ids: list[UUID] = Field(default_factory=list)
    prompt: str | None = None
    negative_prompt: str | None = None
    generation_params: dict[str, Any] = Field(default_factory=dict)

    # Outputs
    output_asset_id: UUID | None = None
    output_asset_ids: list[UUID] = Field(default_factory=list)

    # Status
    status: JobStatus = Field(default=JobStatus.PENDING)
    error_message: str | None = None

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # External references
    external_job_id: str | None = None
    external_url: str | None = None

    # Cost tracking
    credits_used: float | None = None
    cost_usd: float | None = None

    # Quality / Evaluation
    quality_score: float | None = Field(default=None, ge=0.0, le=1.0)
    quality_metrics: dict[str, float] = Field(default_factory=dict)
    human_feedback: str | None = None
    tags: list[str] = Field(default_factory=list)

    # Metadata
    created_by: str | None = None
    project: str | None = None
    notes: str | None = None

    class Config:
        from_attributes = True

    @property
    def duration_seconds(self) -> float | None:
        """Calculate job duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_complete(self) -> bool:
        """Check if job is in a terminal state."""
        return self.status in (
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        )

    def mark_started(self) -> None:
        """Mark job as started."""
        self.status = JobStatus.RUNNING
        self.started_at = datetime.utcnow()

    def mark_completed(self, output_id: UUID) -> None:
        """Mark job as successfully completed."""
        self.status = JobStatus.COMPLETED
        self.output_asset_id = output_id
        self.completed_at = datetime.utcnow()

    def mark_failed(self, error: str) -> None:
        """Mark job as failed."""
        self.status = JobStatus.FAILED
        self.error_message = error
        self.completed_at = datetime.utcnow()


class GenerationJobSummary(BaseModel):
    """Summary statistics for generation jobs."""

    total_jobs: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    success_rate: float = 0.0
    avg_duration_seconds: float | None = None
    total_duration_seconds: float = 0.0
    total_credits_used: float = 0.0
    total_cost_usd: float = 0.0
    avg_quality_score: float | None = None
    by_generator: dict[str, int] = Field(default_factory=dict)

    @classmethod
    def from_jobs(cls, jobs: list[GenerationJob]) -> "GenerationJobSummary":
        """Calculate summary from a list of jobs."""
        if not jobs:
            return cls()

        completed = [j for j in jobs if j.status == JobStatus.COMPLETED]
        failed = [j for j in jobs if j.status == JobStatus.FAILED]
        cancelled = [j for j in jobs if j.status == JobStatus.CANCELLED]

        durations = [j.duration_seconds for j in completed if j.duration_seconds]
        avg_duration = sum(durations) / len(durations) if durations else None

        scores = [j.quality_score for j in completed if j.quality_score is not None]
        avg_quality = sum(scores) / len(scores) if scores else None

        by_gen: dict[str, int] = {}
        for job in jobs:
            gen = job.generator if isinstance(job.generator, str) else job.generator.value
            by_gen[gen] = by_gen.get(gen, 0) + 1

        return cls(
            total_jobs=len(jobs),
            completed=len(completed),
            failed=len(failed),
            cancelled=len(cancelled),
            success_rate=len(completed) / len(jobs) if jobs else 0.0,
            avg_duration_seconds=avg_duration,
            total_duration_seconds=sum(durations) if durations else 0.0,
            total_credits_used=sum(j.credits_used or 0 for j in jobs),
            total_cost_usd=sum(j.cost_usd or 0 for j in jobs),
            avg_quality_score=avg_quality,
            by_generator=by_gen,
        )