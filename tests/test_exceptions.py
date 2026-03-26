"""Tests for exceptions module - RED phase (tests written before implementation)."""

import pytest
from enum import Enum


class TestErrorSeverity:
    """Tests for ErrorSeverity enum."""

    def test_error_severity_recoverable(self):
        """ErrorSeverity should have RECOVERABLE value."""
        from exceptions import ErrorSeverity
        assert ErrorSeverity.RECOVERABLE is not None
        assert isinstance(ErrorSeverity.RECOVERABLE, Enum)

    def test_error_severity_fatal(self):
        """ErrorSeverity should have FATAL value."""
        from exceptions import ErrorSeverity
        assert ErrorSeverity.FATAL is not None
        assert isinstance(ErrorSeverity.FATAL, Enum)

    def test_error_severity_warning(self):
        """ErrorSeverity should have WARNING value."""
        from exceptions import ErrorSeverity
        assert ErrorSeverity.WARNING is not None
        assert isinstance(ErrorSeverity.WARNING, Enum)


class TestProcessingStage:
    """Tests for ProcessingStage enum."""

    def test_processing_stage_audio_extraction(self):
        """ProcessingStage should have AUDIO_EXTRACTION value."""
        from exceptions import ProcessingStage
        assert ProcessingStage.AUDIO_EXTRACTION is not None

    def test_processing_stage_transcription(self):
        """ProcessingStage should have TRANSCRIPTION value."""
        from exceptions import ProcessingStage
        assert ProcessingStage.TRANSCRIPTION is not None


class TestVideoProcessingError:
    """Tests for VideoProcessingError base exception class."""

    def test_error_has_stage_attribute(self):
        """VideoProcessingError should have stage attribute."""
        from exceptions import VideoProcessingError, ProcessingStage, ErrorSeverity
        error = VideoProcessingError(
            stage=ProcessingStage.TRANSCRIPTION,
            severity=ErrorSeverity.RECOVERABLE,
            message="Test error"
        )
        assert error.stage == ProcessingStage.TRANSCRIPTION

    def test_error_has_severity_attribute(self):
        """VideoProcessingError should have severity attribute."""
        from exceptions import VideoProcessingError, ProcessingStage, ErrorSeverity
        error = VideoProcessingError(
            stage=ProcessingStage.TRANSCRIPTION,
            severity=ErrorSeverity.FATAL,
            message="Test error"
        )
        assert error.severity == ErrorSeverity.FATAL

    def test_error_has_original_error(self):
        """VideoProcessingError should store original error."""
        from exceptions import VideoProcessingError, ProcessingStage, ErrorSeverity
        original = ValueError("Original error")
        error = VideoProcessingError(
            stage=ProcessingStage.TRANSCRIPTION,
            severity=ErrorSeverity.RECOVERABLE,
            message="Test error",
            original_error=original
        )
        assert error.original_error is original

    def test_error_has_suggestion(self):
        """VideoProcessingError should have suggestion attribute."""
        from exceptions import VideoProcessingError, ProcessingStage, ErrorSeverity
        error = VideoProcessingError(
            stage=ProcessingStage.TRANSCRIPTION,
            severity=ErrorSeverity.RECOVERABLE,
            message="Test error",
            suggestion="Try again"
        )
        assert error.suggestion == "Try again"

    def test_to_detail_returns_error_detail(self):
        """VideoProcessingError should have to_detail method returning ErrorDetail."""
        from exceptions import VideoProcessingError, ProcessingStage, ErrorSeverity, ErrorDetail
        error = VideoProcessingError(
            stage=ProcessingStage.TRANSCRIPTION,
            severity=ErrorSeverity.RECOVERABLE,
            message="Test error",
            suggestion="Try again"
        )
        detail = error.to_detail()
        assert isinstance(detail, ErrorDetail)
        assert detail.stage == ProcessingStage.TRANSCRIPTION
        assert detail.severity == ErrorSeverity.RECOVERABLE
        assert detail.message == "Test error"
        assert detail.suggestion == "Try again"


class TestAudioExtractionError:
    """Tests for AudioExtractionError exception class."""

    def test_ffmpeg_not_found_error(self):
        """AudioExtractionError should have specific message for ffmpeg not found."""
        from exceptions import AudioExtractionError, ProcessingStage, ErrorSeverity
        error = AudioExtractionError.from_ffmpeg_error(
            stderr="ffmpeg: command not found",
            video_path="/path/to/video.mp4"
        )
        assert error.severity == ErrorSeverity.FATAL
        assert "ffmpeg" in error.message.lower() or "not found" in error.message.lower()

    def test_invalid_video_error(self):
        """AudioExtractionError should handle invalid video file."""
        from exceptions import AudioExtractionError, ProcessingStage, ErrorSeverity
        error = AudioExtractionError.from_ffmpeg_error(
            stderr="Invalid data found",
            video_path="/path/to/invalid.mp4"
        )
        assert error.stage == ProcessingStage.AUDIO_EXTRACTION
        assert error.severity == ErrorSeverity.FATAL

    def test_from_ffmpeg_error_parses_stderr(self):
        """AudioExtractionError.from_ffmpeg_error should parse stderr and create appropriate error."""
        from exceptions import AudioExtractionError, ProcessingStage, ErrorSeverity
        error = AudioExtractionError.from_ffmpeg_error(
            stderr="ffmpeg error: some error occurred",
            video_path="/path/to/video.mp4"
        )
        assert isinstance(error, AudioExtractionError)
        assert error.stage == ProcessingStage.AUDIO_EXTRACTION
        assert error.video_path == "/path/to/video.mp4"
        assert "some error occurred" in error.message