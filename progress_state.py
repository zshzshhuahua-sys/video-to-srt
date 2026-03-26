"""Progress state data classes for video-to-srt processing."""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime


class ProcessingStatus(Enum):
    """Status of a processing task or stage."""
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StageProgress:
    """Progress information for a single processing stage."""
    name: str
    status: ProcessingStatus = ProcessingStatus.IDLE
    percent: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    elapsed_seconds: float = 0
    message: str = ""

    @property
    def elapsed_seconds(self) -> float:
        """Calculate elapsed time in seconds."""
        if self.start_time is None:
            return 0.0
        end = self.end_time if self.end_time else datetime.now()
        return (end - self.start_time).total_seconds()

    @elapsed_seconds.setter
    def elapsed_seconds(self, value: float):
        """Allow setting elapsed_seconds directly (for backwards compatibility)."""
        self._elapsed_seconds = value

    def __post_init__(self):
        if not hasattr(self, '_elapsed_seconds'):
            self._elapsed_seconds = 0.0


@dataclass
class ProcessingTask:
    """Progress information for a complete video processing task."""
    video_path: str
    video_name: str
    video_duration_seconds: Optional[float] = None
    status: ProcessingStatus = ProcessingStatus.IDLE
    stages: Dict[str, StageProgress] = field(default_factory=dict)
    result_paths: Optional[List[str]] = None
    error: Optional[Exception] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def overall_progress_percent(self) -> int:
        """Calculate overall progress percentage across all stages."""
        if not self.stages:
            return 0
        total_percent = sum(stage.percent for stage in self.stages.values())
        return total_percent // len(self.stages)

    @property
    def elapsed_seconds(self) -> float:
        """Calculate total elapsed time in seconds."""
        if self.start_time is None:
            return 0.0
        end = self.end_time if self.end_time else datetime.now()
        return (end - self.start_time).total_seconds()

    @property
    def eta_seconds(self) -> Optional[float]:
        """Estimate time remaining in seconds."""
        if self.status == ProcessingStatus.COMPLETED:
            return None
        if self.status == ProcessingStatus.IDLE:
            return None

        if not self.stages:
            return None

        # Find the currently processing stage
        current_stage = None
        for stage in self.stages.values():
            if stage.status == ProcessingStatus.PROCESSING:
                current_stage = stage
                break

        if current_stage is None:
            return None

        # Calculate ETA based on current stage progress
        if current_stage.percent > 0:
            elapsed = current_stage.elapsed_seconds
            estimated_total = elapsed / (current_stage.percent / 100.0)
            return max(0, estimated_total - elapsed)

        return None


@dataclass
class BatchProgress:
    """Progress information for a batch of video processing tasks."""
    tasks: List[ProcessingTask] = field(default_factory=list)
    current_task_index: int = 0
    historical_speeds: List[float] = field(default_factory=list)

    def __post_init__(self):
        """Auto-detect completed tasks and record their speeds."""
        for task in self.tasks:
            if task.status == ProcessingStatus.COMPLETED:
                self._record_task_speed(task)

    def _record_task_speed(self, task: ProcessingTask):
        """Record the processing speed for a completed task."""
        if task.stages:
            # Use the first stage's elapsed time as approximation
            for stage in task.stages.values():
                if stage.start_time and stage.end_time:
                    elapsed = (stage.end_time - stage.start_time).total_seconds()
                    self.historical_speeds.append(elapsed)
                    break

    @property
    def overall_progress_percent(self) -> int:
        """Calculate overall progress percentage across all tasks."""
        if not self.tasks:
            return 0
        total_percent = sum(task.overall_progress_percent for task in self.tasks)
        return total_percent // len(self.tasks)

    def record_completion(self, task_index: int, elapsed_seconds: float):
        """Record a task completion for historical speed tracking."""
        if 0 <= task_index < len(self.tasks):
            self.historical_speeds.append(elapsed_seconds)
