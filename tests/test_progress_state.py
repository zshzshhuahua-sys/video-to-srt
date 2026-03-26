"""Tests for progress_state module - RED phase (tests written before implementation)."""

import pytest
from enum import Enum
from datetime import datetime


class TestProcessingStatus:
    """Tests for ProcessingStatus enum."""

    def test_status_idle(self):
        """ProcessingStatus should have IDLE value."""
        from progress_state import ProcessingStatus
        assert ProcessingStatus.IDLE is not None
        assert isinstance(ProcessingStatus.IDLE, Enum)

    def test_status_processing(self):
        """ProcessingStatus should have PROCESSING value."""
        from progress_state import ProcessingStatus
        assert ProcessingStatus.PROCESSING is not None

    def test_status_completed(self):
        """ProcessingStatus should have COMPLETED value."""
        from progress_state import ProcessingStatus
        assert ProcessingStatus.COMPLETED is not None

    def test_status_failed(self):
        """ProcessingStatus should have FAILED value."""
        from progress_state import ProcessingStatus
        assert ProcessingStatus.FAILED is not None


class TestStageProgress:
    """Tests for StageProgress dataclass."""

    def test_stage_default_values(self):
        """StageProgress should have correct default values."""
        from progress_state import StageProgress, ProcessingStatus
        stage = StageProgress(name="test_stage")
        assert stage.name == "test_stage"
        assert stage.status == ProcessingStatus.IDLE
        assert stage.percent == 0
        assert stage.start_time is None
        assert stage.end_time is None
        assert stage.elapsed_seconds == 0
        assert stage.message == ""

    def test_stage_duration_when_complete(self):
        """StageProgress should calculate elapsed time when complete."""
        from progress_state import StageProgress, ProcessingStatus
        from datetime import datetime
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 1, 12, 0, 10)
        stage = StageProgress(
            name="test",
            status=ProcessingStatus.COMPLETED,
            start_time=start,
            end_time=end
        )
        assert stage.elapsed_seconds == 10

    def test_stage_duration_when_running(self):
        """StageProgress should calculate elapsed time when running."""
        from progress_state import StageProgress, ProcessingStatus
        from datetime import datetime
        start = datetime(2024, 1, 1, 12, 0, 0)
        # Simulate running for 5 seconds (using a fixed "now" for testing)
        stage = StageProgress(
            name="test",
            status=ProcessingStatus.PROCESSING,
            start_time=start,
            end_time=None
        )
        # When end_time is None, elapsed_seconds should be based on current time
        # We test this by checking the property exists and returns non-negative value
        assert stage.elapsed_seconds >= 0


class TestProcessingTask:
    """Tests for ProcessingTask dataclass."""

    def test_task_default_status_is_idle(self):
        """ProcessingTask default status should be IDLE."""
        from progress_state import ProcessingTask, ProcessingStatus
        task = ProcessingTask(video_path="/path/to/video.mp4", video_name="video.mp4")
        assert task.status == ProcessingStatus.IDLE

    def test_task_overall_progress_percent_zero(self):
        """ProcessingTask overall_progress_percent should be 0 when all stages at 0%."""
        from progress_state import ProcessingTask, StageProgress, ProcessingStatus
        task = ProcessingTask(
            video_path="/path/to/video.mp4",
            video_name="video.mp4",
            video_duration_seconds=100.0,
            stages={
                "stage1": StageProgress(name="stage1", percent=0, status=ProcessingStatus.IDLE),
                "stage2": StageProgress(name="stage2", percent=0, status=ProcessingStatus.IDLE),
            }
        )
        assert task.overall_progress_percent == 0

    def test_task_overall_progress_percent_partial(self):
        """ProcessingTask overall_progress_percent should reflect stage progress."""
        from progress_state import ProcessingTask, StageProgress, ProcessingStatus
        task = ProcessingTask(
            video_path="/path/to/video.mp4",
            video_name="video.mp4",
            video_duration_seconds=100.0,
            stages={
                "stage1": StageProgress(name="stage1", percent=50, status=ProcessingStatus.PROCESSING),
                "stage2": StageProgress(name="stage2", percent=0, status=ProcessingStatus.IDLE),
            }
        )
        # With only stage1 at 50%, overall should be 25%
        assert task.overall_progress_percent == 25

    def test_task_eta_returns_none_when_completed(self):
        """ProcessingTask eta should be None when task is completed."""
        from progress_state import ProcessingTask, StageProgress, ProcessingStatus
        task = ProcessingTask(
            video_path="/path/to/video.mp4",
            video_name="video.mp4",
            video_duration_seconds=100.0,
            status=ProcessingStatus.COMPLETED
        )
        assert task.eta_seconds is None

    def test_task_eta_returns_value_when_processing(self):
        """ProcessingTask eta should return value when task is processing."""
        from progress_state import ProcessingTask, StageProgress, ProcessingStatus
        from datetime import datetime
        task = ProcessingTask(
            video_path="/path/to/video.mp4",
            video_name="video.mp4",
            video_duration_seconds=100.0,
            status=ProcessingStatus.PROCESSING,
            stages={
                "stage1": StageProgress(
                    name="stage1",
                    percent=50,
                    status=ProcessingStatus.PROCESSING,
                    start_time=datetime(2024, 1, 1, 12, 0, 0)
                ),
            }
        )
        # ETA should be a number (positive or None)
        assert task.eta_seconds is None or task.eta_seconds >= 0


class TestBatchProgress:
    """Tests for BatchProgress dataclass."""

    def test_batch_overall_percent(self):
        """BatchProgress overall_percent should aggregate task progress."""
        from progress_state import BatchProgress, ProcessingTask, StageProgress, ProcessingStatus
        task1 = ProcessingTask(
            video_path="/path/to/video1.mp4",
            video_name="video1.mp4",
            video_duration_seconds=100.0,
            stages={
                "stage1": StageProgress(name="stage1", percent=100, status=ProcessingStatus.COMPLETED),
            }
        )
        task2 = ProcessingTask(
            video_path="/path/to/video2.mp4",
            video_name="video2.mp4",
            video_duration_seconds=100.0,
            stages={
                "stage1": StageProgress(name="stage1", percent=50, status=ProcessingStatus.PROCESSING),
            }
        )
        batch = BatchProgress(tasks=[task1, task2])
        # task1 is 100% complete, task2 is 50% complete
        # overall should be (100 + 50) / 2 = 75%
        assert batch.overall_progress_percent == 75

    def test_batch_record_completion_updates_speed(self):
        """BatchProgress should track historical speeds for ETA calculation."""
        from progress_state import BatchProgress, ProcessingTask, StageProgress, ProcessingStatus
        from datetime import datetime, timedelta
        task1 = ProcessingTask(
            video_path="/path/to/video1.mp4",
            video_name="video1.mp4",
            video_duration_seconds=100.0,
            status=ProcessingStatus.COMPLETED,
            stages={
                "stage1": StageProgress(
                    name="stage1",
                    percent=100,
                    status=ProcessingStatus.COMPLETED,
                    start_time=datetime(2024, 1, 1, 12, 0, 0),
                    end_time=datetime(2024, 1, 1, 12, 1, 0)  # 60 seconds
                ),
            }
        )
        batch = BatchProgress(tasks=[task1])
        # Historical speed should track that 100% took 60 seconds
        assert len(batch.historical_speeds) == 1
        assert batch.historical_speeds[0] == 60.0