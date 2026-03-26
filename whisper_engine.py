"""
Whisper 引擎封装
支持 whisper.cpp CoreML 加速
支持延迟加载模式以配合 Streamlit @st.cache_resource
"""
import whisper
import time
import json
import subprocess
from typing import Optional, Callable, Dict, Any

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

from config import WHISPER_MODEL, AUDIO_SAMPLE_RATE
from video_utils import get_video_duration


class WhisperEngine:
    """Whisper 语音识别引擎"""

    def __init__(
        self,
        model_name: str = WHISPER_MODEL,
        lazy_load: bool = False
    ):
        """
        初始化 Whisper 引擎

        Args:
            model_name: 模型大小 (tiny/base/small/medium)
            lazy_load: 如果为 True，模型不会在初始化时加载，而是在首次使用时加载
        """
        self.model_name = model_name
        self.model = None
        self._lazy_load = lazy_load

        if not lazy_load:
            self._load_model()

    def _load_model(self):
        """加载 Whisper 模型"""
        if self.model is not None:
            return  # 已经加载

        print(f"[Whisper] 加载模型: {self.model_name}")
        start = time.time()

        try:
            # 使用 whisper.cpp 的 Python bindings
            # 会自动检测 CoreML 可用性
            self.model = whisper.load_model(self.model_name)
            print(f"[Whisper] 模型加载完成，耗时: {time.time() - start:.1f}s")
        except Exception as e:
            print(f"[Whisper] 模型加载失败: {e}")
            raise

    def _ensure_model_loaded(self):
        """确保模型已加载"""
        if self.model is None:
            self._load_model()

    def get_audio_duration(self, audio_path: str) -> Optional[float]:
        """
        获取音频文件的时长

        Args:
            audio_path: 音频文件路径

        Returns:
            音频时长（秒），如果无法获取则返回 None
        """
        return get_video_duration(audio_path)

    def transcribe(
        self,
        audio_path: str,
        language: str = "zh",
        progress_callback: Optional[Callable[[int, str, Optional[Dict[str, Any]]], None]] = None
    ) -> list:
        """
        识别音频并返回字幕段

        Args:
            audio_path: 音频文件路径
            language: 语言代码 (zh=中文)
            progress_callback: 进度回调函数 (percent, message, detail)
                detail: Dict with keys: stage, segment, total (segment is 0-indexed)

        Returns:
            list: 字幕段列表，每段包含 start, end, text
        """
        self._ensure_model_loaded()

        if progress_callback:
            progress_callback(0, f"开始识别音频: {audio_path}", None)

        print(f"[Whisper] 开始识别: {audio_path}")

        # 构建识别参数
        options = {
            "language": language,
            "task": "transcribe",
            "verbose": False,
            "fp16": False,  # Mac M4 不需要
        }

        try:
            # 执行识别
            start = time.time()
            result = self.model.transcribe(audio_path, **options)
            elapsed = time.time() - start

            segments = result["segments"]
            total_segments = len(segments)

            # 报告每个段的进度
            for i, segment in enumerate(segments):
                if progress_callback:
                    detail = {"stage": "transcription", "segment": i, "total": total_segments}
                    progress_callback(
                        int((i / total_segments) * 100) if total_segments > 0 else 0,
                        f"正在识别段 {i + 1}/{total_segments}: {segment['text'][:20]}...",
                        detail
                    )

            if progress_callback:
                progress_callback(50, f"识别完成，耗时: {elapsed:.1f}s", {"stage": "transcription", "segment": total_segments - 1, "total": total_segments})

            print(f"[Whisper] 识别完成，耗时: {elapsed:.1f}s")
            print(f"[Whisper] 识别出 {len(segments)} 个段落")

            if progress_callback:
                progress_callback(100, f"识别出 {len(segments)} 个段落", {"stage": "transcription", "segment": total_segments - 1, "total": total_segments})

            return segments

        except Exception as e:
            error_msg = f"语音识别失败: {str(e)}"
            print(f"[Whisper] {error_msg}")
            if progress_callback:
                progress_callback(-1, error_msg, None)
            raise

    def transcribe_with_timestamps(
        self,
        audio_path: str,
        language: str = "zh",
        progress_callback: Optional[Callable[[int, str, Optional[Dict[str, Any]]], None]] = None
    ) -> list:
        """
        识别音频并返回带时间戳的段落

        Args:
            audio_path: 音频文件路径
            language: 语言代码
            progress_callback: 进度回调函数

        Returns:
            list: [{'start': float, 'end': float, 'text': str}, ...]
        """
        segments = self.transcribe(audio_path, language, progress_callback)

        result = []
        for seg in segments:
            result.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip()
            })

        return result


def load_whisper_model(model_name: str = WHISPER_MODEL):
    """
    使用 Streamlit cache_resource 缓存模型加载

    这是一个便捷函数，配合 @st.cache_resource 使用：
    ```python
    @st.cache_resource
    def load_model():
        return load_whisper_model_cached("small")

    model = load_model()
    ```

    注意：这个函数本身不使用 @st.cache_resource，因为它可能在无 Streamlit 环境中使用

    Args:
        model_name: 模型名称

    Returns:
        WhisperEngine: 引擎实例（模型已加载）
    """
    engine = WhisperEngine(model_name=model_name, lazy_load=False)
    return engine
