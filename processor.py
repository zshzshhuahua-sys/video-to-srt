"""
视频处理核心逻辑
"""
import os
import ffmpeg
import time
import tempfile
from typing import Optional, Callable, TYPE_CHECKING
from whisper_engine import WhisperEngine
from srt_splitter import SRTSplitter
from config import (
    AUDIO_SAMPLE_RATE,
    SEGMENT_DURATION,
    SUPPORTED_FORMATS,
    TEMP_DIR,
    SRT_SPLIT_SIZE
)
from video_utils import get_video_duration
from exceptions import (
    AudioExtractionError,
    TranscriptionError,
    VideoProcessingError,
)
from progress_state import ProcessingStatus
from checkpoint_manager import CheckpointManager, Checkpoint

if TYPE_CHECKING:
    from progress_tracker import ProgressTracker


class VideoProcessor:
    """视频转 SRT 处理器"""

    def __init__(
        self,
        model_name: str = "small",
        output_dir: str = None,
        split_size: int = SRT_SPLIT_SIZE,
        progress_callback: Optional[Callable] = None
    ):
        """
        初始化处理器

        Args:
            model_name: Whisper 模型名称
            output_dir: 输出目录
            split_size: SRT 切分阈值
            progress_callback: 进度回调函数 (percent, message)
        """
        self.model_name = model_name
        self.output_dir = output_dir or os.path.join(os.path.dirname(__file__), "output")
        self.split_size = split_size
        self.progress_callback = progress_callback or (lambda p, m: print(f"[{p}%] {m}"))

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(TEMP_DIR, exist_ok=True)

        # 初始化组件
        self.whisper = WhisperEngine(model_name)
        self.splitter = SRTSplitter(split_size)

        # 初始化断点管理器
        self.checkpoint_manager = CheckpointManager()

    def process_video(self, video_path: str, custom_filename: str = None, progress_tracker=None) -> str:
        """
        处理单个视频文件

        Args:
            video_path: 视频文件路径
            custom_filename: 自定义输出文件名 (不含扩展名)，None 则使用原文件名
            progress_tracker: 可选的 ProgressTracker 实例用于进度追踪

        Returns:
            str: 生成的 SRT 文件路径 (可能有多个)
        """
        original_filename = os.path.basename(video_path)
        video_duration = get_video_duration(video_path) or 0.0

        # 使用 tracker 或 fallback 到 callback
        if progress_tracker is not None:
            progress_tracker.start_stage("validation", f"开始处理: {original_filename}")
        else:
            self.progress_callback(0, f"开始处理: {original_filename}")

        # 验证文件
        if not os.path.exists(video_path):
            error_msg = f"视频文件不存在: {video_path}"
            if progress_tracker is not None:
                progress_tracker.fail_stage("validation", error_msg)
            raise FileNotFoundError(error_msg)

        ext = os.path.splitext(video_path)[1].lower().lstrip(".")
        if ext not in SUPPORTED_FORMATS:
            error_msg = f"不支持的格式: {ext}，支持: {SUPPORTED_FORMATS}"
            if progress_tracker is not None:
                progress_tracker.fail_stage("validation", error_msg)
            raise ValueError(error_msg)

        if progress_tracker is not None:
            progress_tracker.complete_stage("validation", "验证通过")
            progress_tracker.start_stage("audio_extraction", "正在提取音频...")

        # 确定输出文件名
        if custom_filename:
            # 清理文件名，只保留合法字符
            custom_filename = "".join(c for c in custom_filename if c.isalnum() or c in " _-")
            output_name = custom_filename.strip()
            log_name = f"{original_filename} → {output_name}"
        else:
            output_name = os.path.splitext(original_filename)[0]
            log_name = original_filename

        # 检查是否有未完成的断点可以恢复
        video_name = original_filename  # 使用原始文件名作为 checkpoint key
        checkpoint = None
        if self.checkpoint_manager.has_checkpoint(video_name):
            checkpoint = self.checkpoint_manager.load_checkpoint(video_name)
            if checkpoint and checkpoint.last_segment_index >= 0:
                if progress_tracker is not None:
                    progress_tracker.update_stage("validation", 100, f"发现未完成的处理任务，正在恢复...")
                else:
                    self.progress_callback(5, f"发现未完成的处理任务，从片段 {checkpoint.last_segment_index} 继续...")

        try:
            # Step 1: 提取音频 (可能从断点恢复)
            if checkpoint and checkpoint.audio_path and os.path.exists(checkpoint.audio_path):
                audio_path = checkpoint.audio_path
                if progress_tracker is not None:
                    progress_tracker.update_stage("audio_extraction", 100, "音频已存在，从断点恢复")
                else:
                    self.progress_callback(30, "音频已存在，从断点恢复")
            else:
                audio_path = self._extract_audio(video_path)

            if progress_tracker is not None:
                progress_tracker.update_stage("audio_extraction", 100, "音频提取完成")
                progress_tracker.start_stage("transcription", "正在识别语音...")
            else:
                self.progress_callback(5, "提取音频...")
                self.progress_callback(30, "音频提取完成")

            # Step 2: Whisper 识别
            segments = self._transcribe_audio(audio_path)

            # 保存断点 ( transcription 完成)
            checkpoint = Checkpoint(
                video_path=video_path,
                video_name=video_name,
                audio_path=audio_path,
                processed_segments=segments,
                last_segment_index=len(segments) - 1 if segments else 0,
                stage="transcription_completed"
            )
            self.checkpoint_manager.save_checkpoint(checkpoint)

            if progress_tracker is not None:
                progress_tracker.update_stage("transcription", 100, "语音识别完成")
                progress_tracker.start_stage("srt_generation", "正在生成 SRT...")
            else:
                self.progress_callback(35, "开始语音识别...")
                self.progress_callback(80, "语音识别完成")

            # Step 3: 生成 SRT
            srt_path = self._generate_srt_with_name(segments, output_name)

            if progress_tracker is not None:
                progress_tracker.update_stage("srt_generation", 100, "SRT 生成完成")
                progress_tracker.start_stage("srt_splitting", "正在检查是否需要切分...")
            else:
                self.progress_callback(85, "生成 SRT 文件...")
                self.progress_callback(90, "SRT 文件已生成")

            # Step 4: 检查是否需要切分
            output_files = self.splitter.split_if_needed(srt_path)

            if progress_tracker is not None:
                progress_tracker.update_stage("srt_splitting", 100, "切分检查完成")
                progress_tracker.start_stage("cleanup", "正在清理临时文件...")
            else:
                self.progress_callback(100, "处理完成")

            # 清理临时文件
            self._cleanup([audio_path])

            if progress_tracker is not None:
                progress_tracker.complete_stage("cleanup", "清理完成")
                progress_tracker.complete_stage("processing", "处理完成")
            else:
                self.progress_callback(100, "处理完成")

            # 处理成功，删除断点
            self.checkpoint_manager.delete_checkpoint(video_name)

            return output_files[0] if len(output_files) == 1 else output_files

        except AudioExtractionError:
            # AudioExtractionError 已经包含有用的信息，直接重新抛出
            if progress_tracker is not None:
                progress_tracker.fail_stage("audio_extraction", str(AudioExtractionError))
            raise
        except Exception as e:
            self._cleanup_temp()
            error_msg = f"处理失败: {str(e)}"
            if progress_tracker is not None:
                progress_tracker.fail_stage("processing", error_msg)
            raise RuntimeError(error_msg) from e

    def _extract_audio(self, video_path: str) -> str:
        """
        使用 FFmpeg 提取音频

        Args:
            video_path: 视频文件路径

        Returns:
            str: 音频文件路径

        Raises:
            AudioExtractionError: 当音频提取失败时
        """
        audio_path = os.path.join(TEMP_DIR, f"audio_{int(time.time())}.wav")

        try:
            # 提取音频并转换为 whisper 最佳格式
            stream = ffmpeg.input(video_path)
            stream = ffmpeg.output(
                stream,
                audio_path,
                acodec="pcm_s16le",  # 16bit PCM
                ac=1,  # 单声道
                ar=AUDIO_SAMPLE_RATE,  # 16kHz
                format="wav"
            )
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
            return audio_path

        except ffmpeg.Error as e:
            stderr_str = e.stderr.decode() if e.stderr else str(e)
            raise AudioExtractionError.from_ffmpeg_error(stderr_str, video_path)

    def _transcribe_audio(self, audio_path: str) -> list:
        """
        使用 Whisper 识别音频

        Args:
            audio_path: 音频文件路径

        Returns:
            list: 字幕段列表
        """
        return self.whisper.transcribe_with_timestamps(audio_path, language="zh")

    def _generate_srt(self, segments: list, original_filename: str) -> str:
        """
        生成 SRT 文件

        Args:
            segments: 字幕段列表
            original_filename: 原始视频文件名

        Returns:
            str: SRT 文件路径
        """
        base_name = os.path.splitext(original_filename)[0]
        srt_path = os.path.join(self.output_dir, f"{base_name}.srt")

        with open(srt_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(segments, start=1):
                # 格式化时间
                start_time = self._format_timestamp(seg["start"])
                end_time = self._format_timestamp(seg["end"])

                # 写入 SRT 格式
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{seg['text']}\n")
                f.write("\n")

        return srt_path

    def _generate_srt_with_name(self, segments: list, output_name: str) -> str:
        """
        生成 SRT 文件 (指定输出文件名)

        Args:
            segments: 字幕段列表
            output_name: 输出文件名 (不含扩展名)

        Returns:
            str: SRT 文件路径
        """
        srt_path = os.path.join(self.output_dir, f"{output_name}.srt")

        with open(srt_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(segments, start=1):
                # 格式化时间
                start_time = self._format_timestamp(seg["start"])
                end_time = self._format_timestamp(seg["end"])

                # 写入 SRT 格式
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{seg['text']}\n")
                f.write("\n")

        return srt_path

    def _format_timestamp(self, seconds: float) -> str:
        """
        将秒数转换为 SRT 时间格式

        Args:
            seconds: 秒数

        Returns:
            str: HH:MM:SS,mmm 格式
        """
        # 四舍五入到最接近的毫秒
        total_millis = round(seconds * 1000)
        hours = total_millis // 3600000
        minutes = (total_millis % 3600000) // 60000
        secs = (total_millis % 60000) // 1000
        millis = total_millis % 1000

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _cleanup(self, paths: list):
        """清理临时文件"""
        for path in paths:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass

    def _cleanup_temp(self):
        """清理临时目录"""
        try:
            if os.path.exists(TEMP_DIR):
                for f in os.listdir(TEMP_DIR):
                    self._cleanup([os.path.join(TEMP_DIR, f)])
        except OSError:
            pass
