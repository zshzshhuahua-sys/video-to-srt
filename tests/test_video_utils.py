"""Tests for video_utils module - RED phase (tests written before implementation)."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os


class TestGetVideoDuration:
    """Tests for get_video_duration function."""

    def test_returns_float_for_valid_video(self):
        """get_video_duration should return float for valid video."""
        from video_utils import get_video_duration

        # Mock ffprobe output (format-based output from -show_entries format=duration)
        mock_output = '{"format": {"duration": "120.5"}}'

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(stdout=mock_output, returncode=0)
            result = get_video_duration("/path/to/video.mp4")
            assert result == 120.5
            assert isinstance(result, float)

    def test_returns_none_when_ffprobe_missing(self):
        """get_video_duration should return None when ffprobe is missing."""
        from video_utils import get_video_duration

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("ffprobe not found")
            result = get_video_duration("/path/to/video.mp4")
            assert result is None

    def test_returns_none_for_invalid_path(self):
        """get_video_duration should return None for invalid path."""
        from video_utils import get_video_duration

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(stdout="", returncode=1)
            result = get_video_duration("/nonexistent/path.mp4")
            assert result is None


class TestGetVideoInfo:
    """Tests for get_video_info function."""

    def test_returns_dict_with_required_keys(self):
        """get_video_info should return dict with required keys."""
        from video_utils import get_video_info

        mock_output = '''
        {
            "streams": [
                {
                    "codec_type": "video",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30/1"
                }
            ],
            "format": {
                "duration": "120.5"
            }
        }
        '''

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(stdout=mock_output, returncode=0)
            result = get_video_info("/path/to/video.mp4")

            assert isinstance(result, dict)
            assert "duration" in result
            assert "width" in result
            assert "height" in result
            assert "fps" in result
            assert result["duration"] == 120.5
            assert result["width"] == 1920
            assert result["height"] == 1080
            assert result["fps"] == 30.0

    def test_handles_missing_ffprobe(self):
        """get_video_info should handle missing ffprobe gracefully."""
        from video_utils import get_video_info

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("ffprobe not found")
            result = get_video_info("/path/to/video.mp4")
            assert result is None or result == {}