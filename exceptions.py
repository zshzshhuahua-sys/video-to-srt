"""Error handling and exception hierarchy for video-to-srt processing."""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Any


class ErrorSeverity(Enum):
    """Severity level for errors."""
    RECOVERABLE = "recoverable"
    FATAL = "fatal"
    WARNING = "warning"


class ProcessingStage(Enum):
    """Stages of video processing pipeline."""
    VALIDATION = "validation"
    AUDIO_EXTRACTION = "audio_extraction"
    TRANSCRIPTION = "transcription"
    SRT_GENERATION = "srt_generation"
    SRT_SPLITTING = "srt_splitting"
    CLEANUP = "cleanup"


@dataclass
class ErrorDetail:
    """Detailed error information."""
    stage: ProcessingStage
    severity: ErrorSeverity
    message: str
    original_error: Optional[Exception] = None
    suggestion: Optional[str] = None


class VideoProcessingError(Exception):
    """Base exception for video processing errors."""

    def __init__(
        self,
        stage: ProcessingStage,
        severity: ErrorSeverity,
        message: str,
        original_error: Optional[Exception] = None,
        suggestion: Optional[str] = None,
    ):
        super().__init__(message)
        self.stage = stage
        self.severity = severity
        self.message = message
        self.original_error = original_error
        self.suggestion = suggestion

    def to_detail(self) -> ErrorDetail:
        """Convert exception to ErrorDetail dataclass."""
        return ErrorDetail(
            stage=self.stage,
            severity=self.severity,
            message=self.message,
            original_error=self.original_error,
            suggestion=self.suggestion,
        )


class AudioExtractionError(VideoProcessingError):
    """Error during audio extraction from video."""

    ERROR_MESSAGES = {
        "not_found": "ffmpeg not found. Please install ffmpeg and ensure it's in your PATH.",
        "invalid_video": "Invalid or corrupted video file.",
        "no_audio": "No audio stream found in video.",
        "extraction_failed": "Failed to extract audio from video.",
    }

    def __init__(
        self,
        message: str,
        video_path: Optional[str] = None,
        original_error: Optional[Exception] = None,
        suggestion: Optional[str] = None,
    ):
        super().__init__(
            stage=ProcessingStage.AUDIO_EXTRACTION,
            severity=ErrorSeverity.FATAL,
            message=message,
            original_error=original_error,
            suggestion=suggestion,
        )
        self.video_path = video_path

    @classmethod
    def from_ffmpeg_error(cls, stderr: str, video_path: str) -> "AudioExtractionError":
        """Create AudioExtractionError from ffmpeg error output."""
        stderr_lower = stderr.lower()

        if "not found" in stderr_lower or "command not found" in stderr_lower:
            return cls(
                message=cls.ERROR_MESSAGES["not_found"],
                video_path=video_path,
                suggestion="Install ffmpeg: brew install ffmpeg (macOS) or sudo apt install ffmpeg (Linux)",
            )
        elif "invalid data found" in stderr_lower or "invalid argument" in stderr_lower:
            return cls(
                message=cls.ERROR_MESSAGES["invalid_video"],
                video_path=video_path,
                suggestion="Ensure the video file is not corrupted and try again.",
            )
        elif "no audio stream" in stderr_lower or "audio not found" in stderr_lower:
            return cls(
                message=cls.ERROR_MESSAGES["no_audio"],
                video_path=video_path,
                suggestion="The video file does not contain an audio track.",
            )
        else:
            return cls(
                message=f"Audio extraction failed: {stderr[:200]}",
                video_path=video_path,
                original_error=None,
                suggestion="Check the video file format is supported.",
            )


class TranscriptionError(VideoProcessingError):
    """Error during transcription."""

    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None,
        suggestion: Optional[str] = None,
    ):
        super().__init__(
            stage=ProcessingStage.TRANSCRIPTION,
            severity=ErrorSeverity.RECOVERABLE,
            message=message,
            original_error=original_error,
            suggestion=suggestion,
        )


class SRTSplitError(VideoProcessingError):
    """Error during SRT file splitting."""

    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None,
        suggestion: Optional[str] = None,
    ):
        super().__init__(
            stage=ProcessingStage.SRT_SPLITTING,
            severity=ErrorSeverity.RECOVERABLE,
            message=message,
            original_error=original_error,
            suggestion=suggestion,
        )
