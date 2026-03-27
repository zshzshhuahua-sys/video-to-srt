"""
音频分段模块
使用 ffmpeg 将长音频分片，配合 Whisper 进行转写
"""
import os
import ffmpeg
from typing import List, Dict

from config import TEMP_DIR


class AudioSegmenter:
    """音频分段器，使用 ffmpeg 将长音频按指定时长分片"""

    def __init__(self, segment_duration: int = 600):
        """
        初始化音频分段器

        Args:
            segment_duration: 分段时长（秒），默认 600秒(10分钟)
        """
        self.segment_duration = segment_duration

    def split_by_duration(self, audio_path: str) -> List[str]:
        """
        使用 ffmpeg 将音频分片

        Args:
            audio_path: 音频文件路径

        Returns:
            List[str]: 分片文件路径列表
        """
        # 获取音频总时长
        duration = self._get_audio_duration(audio_path)

        # 计算需要分成的段数（向上取整）
        # 注意：duration 是 float，需要转换为 int 进行整除运算
        num_segments = (int(duration) + self.segment_duration - 1) // self.segment_duration
        # 确保至少有1段
        num_segments = max(1, num_segments)

        segment_paths = []

        for i in range(num_segments):
            # 生成分片文件名
            segment_filename = f"segment_{i}.wav"
            segment_path = os.path.join(TEMP_DIR, segment_filename)

            # 计算每段的起始和结束时间
            start_time = i * self.segment_duration
            end_time = min((i + 1) * self.segment_duration, duration)

            # 使用 ffmpeg 切割音频
            self._cut_audio(audio_path, segment_path, start_time, end_time)
            segment_paths.append(segment_path)

        return segment_paths

    def merge_transcripts(self, segment_results: List[List[Dict]]) -> List[Dict]:
        """
        合并多段转写结果，时间戳自动偏移

        Args:
            segment_results: 多段转写结果列表
                每段结果格式: [{'start': float, 'end': float, 'text': str}, ...]

        Returns:
            List[Dict]: 合并后的字幕段列表
        """
        if not segment_results:
            return []

        merged = []
        for segment_index, segments in enumerate(segment_results):
            # 计算该段的起始时间偏移
            offset = segment_index * self.segment_duration

            for segment in segments:
                # 创建新的段落，时间戳加上偏移量
                merged.append({
                    "start": segment["start"] + offset,
                    "end": segment["end"] + offset,
                    "text": segment["text"]
                })

        return merged

    def _get_audio_duration(self, audio_path: str) -> float:
        """
        获取音频文件的时长

        Args:
            audio_path: 音频文件路径

        Returns:
            float: 音频时长（秒）
        """
        try:
            probe = ffmpeg.probe(audio_path)
            duration = float(probe['format']['duration'])
            return duration
        except ffmpeg.Error as e:
            raise RuntimeError(f"Failed to get audio duration: {e.stderr.decode() if e.stderr else str(e)}")

    def _cut_audio(self, input_path: str, output_path: str, start: float, end: float) -> None:
        """
        使用 ffmpeg 切割音频

        Args:
            input_path: 输入音频路径
            output_path: 输出音频路径
            start: 起始时间（秒）
            end: 结束时间（秒）
        """
        duration = end - start

        stream = ffmpeg.input(input_path, ss=start)
        stream = ffmpeg.output(stream, output_path, acodec="pcm_s16le", ac=1, ar=16000, format="wav", t=duration)
        ffmpeg.run(stream, overwrite_output=True, quiet=True)
