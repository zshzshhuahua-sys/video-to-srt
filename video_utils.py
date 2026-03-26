"""Video utility functions for video-to-srt processing."""

import json
import subprocess
from typing import Optional, Dict, Any


def get_video_duration(video_path: str) -> Optional[float]:
    """Get the duration of a video file using ffprobe.

    Args:
        video_path: Path to the video file

    Returns:
        Duration in seconds as float, or None if unable to determine
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            video_path
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        duration = data.get("format", {}).get("duration")
        if duration is not None:
            return float(duration)
        return None

    except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired):
        return None


def get_video_info(video_path: str) -> Optional[Dict[str, Any]]:
    """Get detailed information about a video file using ffprobe.

    Args:
        video_path: Path to the video file

    Returns:
        Dictionary with duration, width, height, fps keys, or None if unable to determine
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "stream=width,height,r_frame_rate,codec_type",
            "-show_entries", "format=duration",
            "-of", "json",
            video_path
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        fmt = data.get("format", {})

        # Find video stream
        video_stream = None
        for stream in streams:
            if stream.get("codec_type") == "video":
                video_stream = stream
                break

        if video_stream is None:
            return None

        # Parse frame rate
        fps_str = video_stream.get("r_frame_rate", "0/1")
        if "/" in fps_str:
            num, denom = fps_str.split("/")
            fps = float(num) / float(denom) if float(denom) != 0 else 0.0
        else:
            fps = float(fps_str)

        return {
            "duration": float(fmt.get("duration", 0)),
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "fps": fps,
        }

    except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired, ValueError):
        return None
