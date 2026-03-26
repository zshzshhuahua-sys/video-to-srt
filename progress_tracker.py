"""Progress tracker for video-to-srt processing."""

from typing import Optional, Callable, Dict, Any
from datetime import datetime

from progress_state import (
    ProcessingTask,
    StageProgress,
    ProcessingStatus,
)
from exceptions import VideoProcessingError


class ProgressTracker:
    """Tracks progress for a video processing task."""

    def __init__(
        self,
        video_path: str,
        video_name: str,
        video_duration: float,
        progress_callback: Optional[Callable[[str, bool], None]] = None,
    ):
        """Initialize the progress tracker.

        Args:
            video_path: Path to the video file
            video_name: Name of the video file
            video_duration: Duration of the video in seconds
            progress_callback: Optional callback for progress updates (message, is_error)
        """
        self.video_path = video_path
        self.video_name = video_name
        self.video_duration = video_duration
        self.progress_callback = progress_callback
        self._last_emit_time: Optional[datetime] = None
        self._emit_interval_seconds = 1.0  # Throttle emit to once per second

        self.task = ProcessingTask(
            video_path=video_path,
            video_name=video_name,
            video_duration_seconds=video_duration,
            status=ProcessingStatus.IDLE,
        )

    def start_stage(self, stage_name: str, message: str = ""):
        """Start a new processing stage.

        Args:
            stage_name: Name of the stage (e.g., 'audio_extraction')
            message: Initial status message
        """
        stage = StageProgress(
            name=stage_name,
            status=ProcessingStatus.PROCESSING,
            percent=0,
            start_time=datetime.now(),
            message=message,
        )
        self.task.stages[stage_name] = stage
        self.task.status = ProcessingStatus.PROCESSING
        self._emit_progress(message, is_error=False)

    def update_stage(
        self,
        stage_name: str,
        percent: int,
        message: str = "",
        stage_detail: Optional[str] = None,
    ):
        """Update progress for a stage.

        Args:
            stage_name: Name of the stage to update
            percent: Progress percentage (0-100)
            message: Status message
            stage_detail: Optional detailed progress info
        """
        if stage_name not in self.task.stages:
            self.start_stage(stage_name, message)

        stage = self.task.stages[stage_name]
        stage.percent = min(100, max(0, percent))
        if message:
            stage.message = message

        # Calculate ETA
        eta = self._calculate_stage_eta(stage_name)
        if eta is not None:
            formatted_eta = self._format_duration(eta)
            full_message = f"{message} ({formatted_eta} remaining)" if message else f"ETA: {formatted_eta}"
        else:
            full_message = message

        self._emit_progress(full_message, is_error=False)

    def complete_stage(self, stage_name: str, message: str = ""):
        """Mark a stage as completed.

        Args:
            stage_name: Name of the stage to complete
            message: Completion message
        """
        if stage_name not in self.task.stages:
            self.start_stage(stage_name, message)

        stage = self.task.stages[stage_name]
        stage.status = ProcessingStatus.COMPLETED
        stage.percent = 100
        stage.end_time = datetime.now()
        if message:
            stage.message = message

        # Check if all stages are complete
        all_complete = all(
            s.status == ProcessingStatus.COMPLETED
            for s in self.task.stages.values()
        )
        if all_complete:
            self.task.status = ProcessingStatus.COMPLETED
            self.task.end_time = datetime.now()

        self._emit_progress(message, is_error=False)

    def fail_stage(self, stage_name: str, error_message: str):
        """Mark a stage as failed.

        Args:
            stage_name: Name of the stage that failed
            error_message: Error message describing the failure
        """
        if stage_name not in self.task.stages:
            self.start_stage(stage_name, "")

        stage = self.task.stages[stage_name]
        stage.status = ProcessingStatus.FAILED
        stage.end_time = datetime.now()
        stage.message = error_message

        self.task.status = ProcessingStatus.FAILED
        self.task.end_time = datetime.now()
        self.task.error = VideoProcessingError(
            stage=self._get_stage_processing_stage(stage_name),
            severity=VideoProcessingError(
                stage=self._get_stage_processing_stage(stage_name),
                severity=VideoProcessingError,
                message=error_message,
            ).severity if hasattr(VideoProcessingError, 'severity') else None,
            message=error_message,
        )

        self._emit_progress(f"ERROR: {error_message}", is_error=True)

    def _get_stage_processing_stage(self, stage_name: str):
        """Map stage name to ProcessingStage enum value."""
        from exceptions import ProcessingStage
        stage_mapping = {
            "validation": ProcessingStage.VALIDATION,
            "audio_extraction": ProcessingStage.AUDIO_EXTRACTION,
            "transcription": ProcessingStage.TRANSCRIPTION,
            "srt_generation": ProcessingStage.SRT_GENERATION,
            "srt_splitting": ProcessingStage.SRT_SPLITTING,
            "cleanup": ProcessingStage.CLEANUP,
        }
        return stage_mapping.get(stage_name, ProcessingStage.VALIDATION)

    def _calculate_stage_eta(self, stage_name: str) -> Optional[float]:
        """Calculate estimated time remaining for a stage.

        Args:
            stage_name: Name of the stage

        Returns:
            Estimated seconds remaining, or None if cannot calculate
        """
        if stage_name not in self.task.stages:
            return None

        stage = self.task.stages[stage_name]
        if stage.percent <= 0:
            return None

        elapsed = stage.elapsed_seconds
        if elapsed <= 0:
            return None

        # Estimate total time based on current progress
        estimated_total = elapsed / (stage.percent / 100.0)
        remaining = estimated_total - elapsed

        return max(0, remaining)

    def _emit_progress(self, message: str, is_error: bool = False):
        """Emit progress update with throttling.

        Args:
            message: Progress message
            is_error: Whether this is an error message
        """
        if self.progress_callback is None:
            return

        now = datetime.now()
        if self._last_emit_time is None:
            self._last_emit_time = now
            self.progress_callback(message, is_error)
            return

        elapsed = (now - self._last_emit_time).total_seconds()
        if elapsed >= self._emit_interval_seconds or is_error:
            self._last_emit_time = now
            self.progress_callback(message, is_error)

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in seconds to human-readable string.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted string (e.g., "1:30", "1:01:30")
        """
        if seconds < 0:
            seconds = 0

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
