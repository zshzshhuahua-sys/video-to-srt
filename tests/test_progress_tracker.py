"""Tests for progress_tracker module - RED phase (tests written before implementation)."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime


class TestProgressTracker:
    """Tests for ProgressTracker class."""

    def test_start_stage_creates_stage(self):
        """start_stage should create a new stage in the task."""
        from progress_tracker import ProgressTracker
        callback = Mock()
        tracker = ProgressTracker(
            video_path="/path/to/video.mp4",
            video_name="video.mp4",
            video_duration=100.0,
            progress_callback=callback
        )
        tracker.start_stage("audio_extraction", "Starting audio extraction")

        assert "audio_extraction" in tracker.task.stages
        stage = tracker.task.stages["audio_extraction"]
        assert stage.percent == 0
        assert stage.message == "Starting audio extraction"

    def test_update_stage_updates_percent(self):
        """update_stage should update the stage percent."""
        from progress_tracker import ProgressTracker
        callback = Mock()
        tracker = ProgressTracker(
            video_path="/path/to/video.mp4",
            video_name="video.mp4",
            video_duration=100.0,
            progress_callback=callback
        )
        tracker.start_stage("audio_extraction", "Starting")
        tracker.update_stage("audio_extraction", 50, "Halfway done")

        stage = tracker.task.stages["audio_extraction"]
        assert stage.percent == 50
        assert stage.message == "Halfway done"

    def test_complete_stage_sets_status(self):
        """complete_stage should set stage status to COMPLETED."""
        from progress_tracker import ProgressTracker
        from progress_state import ProcessingStatus
        callback = Mock()
        tracker = ProgressTracker(
            video_path="/path/to/video.mp4",
            video_name="video.mp4",
            video_duration=100.0,
            progress_callback=callback
        )
        tracker.start_stage("audio_extraction", "Starting")
        tracker.complete_stage("audio_extraction", "Audio extraction complete")

        stage = tracker.task.stages["audio_extraction"]
        assert stage.status == ProcessingStatus.COMPLETED
        assert stage.percent == 100
        assert stage.message == "Audio extraction complete"

    def test_fail_stage_sets_error(self):
        """fail_stage should set stage status to FAILED and record error."""
        from progress_tracker import ProgressTracker
        from progress_state import ProcessingStatus
        callback = Mock()
        tracker = ProgressTracker(
            video_path="/path/to/video.mp4",
            video_name="video.mp4",
            video_duration=100.0,
            progress_callback=callback
        )
        tracker.start_stage("audio_extraction", "Starting")
        tracker.fail_stage("audio_extraction", "ffmpeg not found")

        stage = tracker.task.stages["audio_extraction"]
        assert stage.status == ProcessingStatus.FAILED
        assert tracker.task.status == ProcessingStatus.FAILED
        assert tracker.task.error is not None
        assert "ffmpeg not found" in str(tracker.task.error)

    def test_format_duration_seconds(self):
        """_format_duration should format seconds correctly."""
        from progress_tracker import ProgressTracker
        result = ProgressTracker._format_duration(45)
        assert result == "0:45"

    def test_format_duration_minutes(self):
        """_format_duration should format minutes and seconds correctly."""
        from progress_tracker import ProgressTracker
        result = ProgressTracker._format_duration(125)  # 2:05
        assert result == "2:05"

    def test_format_duration_hours(self):
        """_format_duration should format hours, minutes and seconds correctly."""
        from progress_tracker import ProgressTracker
        result = ProgressTracker._format_duration(3665)  # 1:01:05
        assert result == "1:01:05"