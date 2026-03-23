"""
Video processor.

Handles video-specific operations including keyframe extraction
and audio transcription.
"""

from pathlib import Path
from typing import Any

import cv2

from ingest_core.config import Settings, get_settings
from ingest_core.processors.base import BaseProcessor


class VideoProcessor(BaseProcessor):
    """
    Process video files.

    Supports: MP4, MOV, AVI, WebM, MKV
    Max duration: 30 seconds (configurable)

    Features:
    - Keyframe extraction (scene detection or interval)
    - Audio extraction
    - Transcription via Whisper
    """

    name = "video"
    supported_extensions = [".mp4", ".mov", ".avi", ".webm", ".mkv"]

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._whisper_model = None

    def _get_whisper_model(self):
        """Lazy-load Whisper model."""
        if self._whisper_model is None:
            import whisper
            self._whisper_model = whisper.load_model(self.settings.processing.whisper_model)
        return self._whisper_model

    async def validate(self, file_path: Path) -> tuple[bool, str | None]:
        """Validate video file and check duration."""
        try:
            cap = cv2.VideoCapture(str(file_path))

            if not cap.isOpened():
                return False, "Could not open video file"

            # Check duration
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            duration = frame_count / fps if fps > 0 else 0

            cap.release()

            max_duration = self.settings.processing.max_video_duration_seconds
            if duration > max_duration:
                return False, f"Video duration ({duration:.1f}s) exceeds maximum ({max_duration}s)"

            return True, None

        except Exception as e:
            return False, f"Invalid video: {str(e)}"

    async def extract_metadata(self, file_path: Path) -> dict[str, Any]:
        """Extract video metadata."""
        cap = cv2.VideoCapture(str(file_path))

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0

            return {
                "width": width,
                "height": height,
                "aspect_ratio": round(width / height, 3) if height > 0 else 0,
                "duration_seconds": round(duration, 2),
                "frame_rate": round(fps, 2),
                "total_frames": frame_count,
                "file_size_bytes": file_path.stat().st_size,
            }
        finally:
            cap.release()

    async def generate_thumbnail(
        self,
        file_path: Path,
        output_path: Path,
        size: tuple[int, int] = (256, 256),
    ) -> Path | None:
        """Generate thumbnail from first frame."""
        try:
            cap = cv2.VideoCapture(str(file_path))
            ret, frame = cap.read()
            cap.release()

            if not ret:
                return None

            # Resize
            frame = cv2.resize(frame, size, interpolation=cv2.INTER_LANCZOS4)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(output_path), frame)

            return output_path
        except Exception:
            return None

    async def extract_keyframes(
        self,
        file_path: Path,
        output_dir: Path,
        method: str = "scene",
        interval_seconds: float = 2.0,
    ) -> list[dict]:
        """
        Extract keyframes from video.

        Args:
            file_path: Video file path
            output_dir: Directory to save keyframes
            method: "scene" (scene detection), "interval" (fixed interval), "both"
            interval_seconds: Interval for interval-based extraction

        Returns:
            list[dict]: List of keyframe info
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        keyframes = []

        cap = cv2.VideoCapture(str(file_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        try:
            if method in ("interval", "both"):
                # Extract at fixed intervals
                interval_frames = int(fps * interval_seconds)

                for frame_num in range(0, frame_count, interval_frames):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                    ret, frame = cap.read()

                    if ret:
                        timestamp = frame_num / fps
                        output_path = output_dir / f"keyframe_{frame_num:06d}.jpg"
                        cv2.imwrite(str(output_path), frame)

                        keyframes.append({
                            "frame_number": frame_num,
                            "timestamp_seconds": round(timestamp, 2),
                            "storage_path": str(output_path),
                            "is_scene_change": False,
                        })

            # Scene detection would go here (using histogram comparison)
            # Simplified for now - can be extended with proper scene detection

        finally:
            cap.release()

        return keyframes

    async def transcribe_audio(self, file_path: Path) -> dict:
        """
        Transcribe audio from video using Whisper.

        Returns:
            dict: Transcript with segments
        """
        try:
            model = self._get_whisper_model()
            result = model.transcribe(str(file_path))

            return {
                "transcript": result["text"],
                "segments": [
                    {
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": seg["text"],
                    }
                    for seg in result["segments"]
                ],
                "language": result.get("language", "unknown"),
            }
        except Exception as e:
            return {
                "transcript": None,
                "error": str(e),
            }
