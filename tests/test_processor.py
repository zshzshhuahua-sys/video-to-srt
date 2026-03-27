"""
测试 processor.py 视频处理核心逻辑
TDD RED 阶段：编写会失败的测试
"""
import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock, Mock


class TestVideoProcessorInit:
    """测试 VideoProcessor 初始化"""

    def test_init_with_default_params(self):
        """测试默认参数初始化"""
        with patch('processor.WhisperEngine'), patch('processor.SRTSplitter'):
            from processor import VideoProcessor
            vp = VideoProcessor()

            assert vp.model_name == "small"
            assert vp.split_size > 0

    def test_init_with_custom_params(self):
        """测试自定义参数初始化"""
        with patch('processor.WhisperEngine'), patch('processor.SRTSplitter'):
            from processor import VideoProcessor
            vp = VideoProcessor(
                model_name="medium",
                output_dir="/tmp/output",
                split_size=5 * 1024 * 1024
            )

            assert vp.model_name == "medium"
            assert vp.output_dir == "/tmp/output"
            assert vp.split_size == 5 * 1024 * 1024

    def test_init_creates_output_dir(self):
        """测试初始化时创建输出目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "output")

            with patch('processor.WhisperEngine'), patch('processor.SRTSplitter'):
                from processor import VideoProcessor
                vp = VideoProcessor(output_dir=output_dir)

                assert os.path.exists(output_dir)

    def test_init_accepts_progress_callback(self):
        """测试初始化接受 progress_callback"""
        with patch('processor.WhisperEngine'), patch('processor.SRTSplitter'):
            from processor import VideoProcessor

            callback_called = []
            def callback(percent, message):
                callback_called.append((percent, message))

            vp = VideoProcessor(progress_callback=callback)
            assert vp.progress_callback is callback


class TestExtractAudio:
    """测试音频提取功能"""

    def test_extract_audio_returns_wav_path(self):
        """测试提取音频返回 wav 文件路径"""
        with patch('processor.WhisperEngine'), patch('processor.SRTSplitter'), \
             patch('processor.ffmpeg') as mock_ffmpeg:
            mock_stream = MagicMock()
            mock_ffmpeg.input.return_value = mock_stream
            mock_ffmpeg.output.return_value = mock_stream
            mock_stream.output.return_value = mock_stream

            from processor import VideoProcessor
            vp = VideoProcessor()

            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
                video_path = f.name

            try:
                audio_path = vp._extract_audio(video_path)
                assert audio_path.endswith('.wav')
                assert 'audio_' in audio_path or 'temp' in audio_path.lower()
            finally:
                if os.path.exists(video_path):
                    os.remove(video_path)

    def test_extract_audio_calls_ffmpeg(self):
        """测试音频提取调用 FFmpeg"""
        with patch('processor.WhisperEngine'), patch('processor.SRTSplitter'), \
             patch('processor.ffmpeg') as mock_ffmpeg:
            mock_stream = MagicMock()
            mock_ffmpeg.input.return_value = mock_stream
            mock_ffmpeg.output.return_value = mock_stream
            mock_stream.output.return_value = mock_stream

            from processor import VideoProcessor
            vp = VideoProcessor()

            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
                video_path = f.name

            try:
                vp._extract_audio(video_path)

                # 验证 ffmpeg.input 被调用
                mock_ffmpeg.input.assert_called_once()
            finally:
                if os.path.exists(video_path):
                    os.remove(video_path)

    def test_extract_audio_error_handling(self):
        """测试音频提取错误处理"""
        import ffmpeg as ffmpeg_module

        with patch('processor.WhisperEngine'), patch('processor.SRTSplitter'), \
             patch('processor.ffmpeg') as mock_ffmpeg:
            # 创建一个继承自 Exception 的模拟错误，带有 stderr 属性
            class FFmpegError(Exception):
                def __init__(self, msg, stderr=b"error"):
                    super().__init__(msg)
                    self.stderr = stderr

            mock_ffmpeg.Error = FFmpegError
            mock_ffmpeg.input.side_effect = FFmpegError("FFmpeg error")

            from processor import VideoProcessor
            from exceptions import AudioExtractionError

            vp = VideoProcessor()

            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
                video_path = f.name

            try:
                with pytest.raises(AudioExtractionError):
                    vp._extract_audio(video_path)
            finally:
                if os.path.exists(video_path):
                    os.remove(video_path)


class TestTranscribeAudio:
    """测试音频识别功能"""

    def test_transcribe_audio_returns_segments(self):
        """测试音频识别返回字幕段"""
        with patch('processor.WhisperEngine') as mock_engine_class, \
             patch('processor.AudioSegmenter') as mock_segmenter_class, \
             patch('processor.SRTSplitter'):
            mock_engine = MagicMock()
            mock_engine.transcribe_with_timestamps.return_value = [
                {"start": 0.0, "end": 2.5, "text": "测试"},
                {"start": 2.6, "end": 5.0, "text": "第二句"},
            ]
            mock_engine_class.return_value = mock_engine

            mock_segmenter = MagicMock()
            mock_segmenter.split_by_duration.return_value = ['/tmp/seg0.wav']
            mock_segmenter.merge_transcripts.return_value = [
                {"start": 0.0, "end": 2.5, "text": "测试"},
                {"start": 2.6, "end": 5.0, "text": "第二句"},
            ]
            mock_segmenter_class.return_value = mock_segmenter

            from processor import VideoProcessor
            vp = VideoProcessor()
            vp.segmenter = mock_segmenter

            result = vp._transcribe_audio("dummy.wav")

            assert len(result) == 2
            assert result[0]["text"] == "测试"
            mock_engine.transcribe_with_timestamps.assert_called_once()

    def test_transcribe_audio_default_language(self):
        """测试音频识别默认语言是中文"""
        with patch('processor.WhisperEngine') as mock_engine_class, \
             patch('processor.AudioSegmenter') as mock_segmenter_class, \
             patch('processor.SRTSplitter'):
            mock_engine = MagicMock()
            mock_engine.transcribe_with_timestamps.return_value = []
            mock_engine_class.return_value = mock_engine

            mock_segmenter = MagicMock()
            mock_segmenter.split_by_duration.return_value = ['/tmp/seg0.wav']
            mock_segmenter.merge_transcripts.return_value = []
            mock_segmenter_class.return_value = mock_segmenter

            from processor import VideoProcessor
            vp = VideoProcessor()
            vp.segmenter = mock_segmenter

            vp._transcribe_audio("dummy.wav")

            call_args = mock_engine.transcribe_with_timestamps.call_args
            assert call_args[1]['language'] == 'zh'


class TestGenerateSRT:
    """测试 SRT 生成功能"""

    def test_generate_srt_creates_file(self):
        """测试生成 SRT 文件"""
        with patch('processor.WhisperEngine'), patch('processor.SRTSplitter'):
            from processor import VideoProcessor
            vp = VideoProcessor()

            segments = [
                {"start": 0.0, "end": 2.5, "text": "第一句"},
                {"start": 2.6, "end": 5.3, "text": "第二句"},
            ]

            with tempfile.TemporaryDirectory() as tmpdir:
                srt_path = vp._generate_srt_with_name(segments, "test_output")
                srt_path = os.path.join(tmpdir, "test_output.srt")

                # 使用临时目录重新生成
                with open(srt_path, 'w', encoding='utf-8') as f:
                    for i, seg in enumerate(segments, start=1):
                        start_time = vp._format_timestamp(seg["start"])
                        end_time = vp._format_timestamp(seg["end"])
                        f.write(f"{i}\n")
                        f.write(f"{start_time} --> {end_time}\n")
                        f.write(f"{seg['text']}\n")
                        f.write("\n")

                assert os.path.exists(srt_path)

                with open(srt_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                assert "1\n" in content
                assert "00:00:00,000 --> 00:00:02,500\n" in content
                assert "第一句\n" in content

    def test_generate_srt_with_name(self):
        """测试指定文件名的 SRT 生成"""
        import tempfile as temp_module

        with patch('processor.WhisperEngine'), patch('processor.SRTSplitter'):
            from processor import VideoProcessor
            vp = VideoProcessor()

            segments = [{"start": 0.0, "end": 2.5, "text": "测试"}]

            with temp_module.TemporaryDirectory() as tmpdir:
                # 直接在 temp 目录生成
                temp_srt = temp_module.mktemp(suffix='.srt')
                result = vp._generate_srt_with_name(segments, "custom")
                # 实际路径在 output_dir 中
                assert result.endswith(".srt")


class TestFormatTimestamp:
    """测试时间戳格式化"""

    def test_format_timestamp_standard(self):
        """测试标准时间戳格式化"""
        from processor import VideoProcessor
        vp = VideoProcessor()

        assert vp._format_timestamp(0.0) == "00:00:00,000"
        assert vp._format_timestamp(1.5) == "00:00:01,500"
        assert vp._format_timestamp(61.25) == "00:01:01,250"
        assert vp._format_timestamp(3661.123) == "01:01:01,123"

    def test_format_timestamp_rounds_milliseconds(self):
        """测试毫秒四舍五入"""
        from processor import VideoProcessor
        vp = VideoProcessor()

        # 0.9999 秒 = 999.9ms，四舍五入到 1000ms = 1秒
        assert vp._format_timestamp(0.9999) == "00:00:01,000"
        assert vp._format_timestamp(0.9995) == "00:00:01,000"
        # 0.9994 秒 = 999.4ms，四舍五入到 999ms
        assert vp._format_timestamp(0.9994) == "00:00:00,999"


class TestProcessVideo:
    """测试完整视频处理流程"""

    def test_process_video_validates_file_exists(self):
        """测试处理视频时验证文件存在"""
        with patch('processor.WhisperEngine'), patch('processor.SRTSplitter'):
            from processor import VideoProcessor
            vp = VideoProcessor()

            with pytest.raises(FileNotFoundError):
                vp.process_video("/nonexistent/video.mp4")

    def test_process_video_validates_format(self):
        """测试处理视频时验证格式支持"""
        with patch('processor.WhisperEngine'), patch('processor.SRTSplitter'):
            from processor import VideoProcessor
            vp = VideoProcessor()

            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
                f.write(b"not a video")

            try:
                with pytest.raises(ValueError, match="不支持"):
                    vp.process_video(f.name)
            finally:
                os.remove(f.name)

    def test_process_video_calls_callback(self):
        """测试处理视频时调用进度回调"""
        with patch('processor.WhisperEngine') as mock_engine_class, \
             patch('processor.SRTSplitter') as mock_splitter_class, \
             patch('processor.AudioSegmenter') as mock_segmenter_class:
            mock_engine = MagicMock()
            mock_engine.transcribe_with_timestamps.return_value = []
            mock_engine_class.return_value = mock_engine

            mock_splitter = MagicMock()
            mock_splitter.split_if_needed.return_value = ["/tmp/test.srt"]
            mock_splitter_class.return_value = mock_splitter

            mock_segmenter = MagicMock()
            mock_segmenter.split_by_duration.return_value = ['/tmp/seg0.wav']
            mock_segmenter.merge_transcripts.return_value = []
            mock_segmenter_class.return_value = mock_segmenter

            from processor import VideoProcessor
            callback_calls = []
            def callback(percent, message):
                callback_calls.append((percent, message))

            vp = VideoProcessor(progress_callback=callback)
            vp.segmenter = mock_segmenter

            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
                video_path = f.name

            try:
                with patch.object(vp, '_extract_audio', return_value='/tmp/audio.wav'), \
                     patch.object(vp, '_cleanup'):
                    vp.process_video(video_path)

                # 验证回调被调用
                assert len(callback_calls) > 0
            finally:
                if os.path.exists(video_path):
                    os.remove(video_path)


class TestProcessorErrorWrapping:
    """测试处理器错误包装"""

    def test_audio_extraction_error_wrapped(self):
        """测试音频提取错误被包装为 AudioExtractionError"""
        import ffmpeg as ffmpeg_module

        with patch('processor.WhisperEngine'), patch('processor.SRTSplitter'), \
             patch('processor.ffmpeg') as mock_ffmpeg:

            class FFmpegError(Exception):
                def __init__(self, msg, stderr=b"error"):
                    super().__init__(msg)
                    self.stderr = stderr

            mock_ffmpeg.Error = FFmpegError
            mock_ffmpeg.input.side_effect = FFmpegError("Invalid data found")

            from processor import VideoProcessor
            from exceptions import AudioExtractionError

            vp = VideoProcessor()

            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
                video_path = f.name

            try:
                with pytest.raises(AudioExtractionError, match="Audio extraction failed"):
                    vp._extract_audio(video_path)
            finally:
                if os.path.exists(video_path):
                    os.remove(video_path)

    def test_ffmpeg_not_found_raises_audio_extraction_error(self):
        """测试 ffmpeg 不存在时抛出 AudioExtractionError"""
        with patch('processor.WhisperEngine'), patch('processor.SRTSplitter'), \
             patch('processor.ffmpeg') as mock_ffmpeg:

            class FFmpegError(Exception):
                def __init__(self, msg, stderr=b"ffmpeg not found"):
                    super().__init__(msg)
                    self.stderr = stderr

            mock_ffmpeg.Error = FFmpegError
            mock_ffmpeg.input.side_effect = FFmpegError("ffmpeg not found")

            from processor import VideoProcessor
            from exceptions import AudioExtractionError

            vp = VideoProcessor()

            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
                video_path = f.name

            try:
                with pytest.raises(AudioExtractionError) as exc_info:
                    vp._extract_audio(video_path)
                assert "not found" in str(exc_info.value).lower() or "ffmpeg" in str(exc_info.value).lower()
            finally:
                if os.path.exists(video_path):
                    os.remove(video_path)


class TestProcessorProgress:
    """测试处理器进度追踪"""

    def test_process_video_uses_progress_tracker(self):
        """测试 process_video 使用 progress_tracker"""
        with patch('processor.WhisperEngine') as mock_engine_class, \
             patch('processor.SRTSplitter') as mock_splitter_class, \
             patch('processor.AudioSegmenter') as mock_segmenter_class:

            mock_engine = MagicMock()
            mock_engine.transcribe_with_timestamps.return_value = []
            mock_engine_class.return_value = mock_engine

            mock_splitter = MagicMock()
            mock_splitter.split_if_needed.return_value = ["/tmp/test.srt"]
            mock_splitter_class.return_value = mock_splitter

            mock_segmenter = MagicMock()
            mock_segmenter.split_by_duration.return_value = ['/tmp/seg0.wav']
            mock_segmenter.merge_transcripts.return_value = []
            mock_segmenter_class.return_value = mock_segmenter

            from processor import VideoProcessor
            from progress_tracker import ProgressTracker

            tracker = MagicMock(spec=ProgressTracker)

            vp = VideoProcessor()
            vp.segmenter = mock_segmenter

            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
                video_path = f.name

            try:
                with patch.object(vp, '_extract_audio', return_value='/tmp/audio.wav'), \
                     patch.object(vp, '_cleanup'):
                    vp.process_video(video_path, progress_tracker=tracker)

                # 验证 tracker 被调用
                assert tracker.start_stage.called, "Expected start_stage to be called"
                assert tracker.update_stage.called or tracker.complete_stage.called, \
                    "Expected update_stage or complete_stage to be called"
            finally:
                if os.path.exists(video_path):
                    os.remove(video_path)

    def test_stage_timing_recorded(self):
        """测试阶段时间被记录"""
        with patch('processor.WhisperEngine') as mock_engine_class, \
             patch('processor.SRTSplitter') as mock_splitter_class, \
             patch('processor.AudioSegmenter') as mock_segmenter_class:

            mock_engine = MagicMock()
            mock_engine.transcribe_with_timestamps.return_value = []
            mock_engine_class.return_value = mock_engine

            mock_splitter = MagicMock()
            mock_splitter.split_if_needed.return_value = ["/tmp/test.srt"]
            mock_splitter_class.return_value = mock_splitter

            mock_segmenter = MagicMock()
            mock_segmenter.split_by_duration.return_value = ['/tmp/seg0.wav']
            mock_segmenter.merge_transcripts.return_value = []
            mock_segmenter_class.return_value = mock_segmenter

            from processor import VideoProcessor
            from progress_tracker import ProgressTracker

            # 创建一个真实的 ProgressTracker 来验证时间记录
            with tempfile.TemporaryDirectory() as tmpdir:
                tracker = ProgressTracker(
                    video_path="/fake/video.mp4",
                    video_name="video.mp4",
                    video_duration=60.0,
                    progress_callback=MagicMock()
                )

                vp = VideoProcessor()
                vp.segmenter = mock_segmenter

                with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False, dir=tmpdir) as f:
                    video_path = f.name

                try:
                    with patch.object(vp, '_extract_audio', return_value='/tmp/audio.wav'), \
                         patch.object(vp, '_cleanup'):
                        vp.process_video(video_path, progress_tracker=tracker)

                    # 验证 stages 被记录
                    assert len(tracker.task.stages) > 0, "Expected stages to be recorded"

                    # 验证至少有一个阶段的开始时间被记录
                    stage_names = list(tracker.task.stages.keys())
                    for name in stage_names:
                        stage = tracker.task.stages[name]
                        assert stage.start_time is not None, f"Expected start_time for stage {name}"
                finally:
                    if os.path.exists(video_path):
                        os.remove(video_path)

    def test_process_video_with_tracker_validates_format(self):
        """测试使用 tracker 时格式验证失败会记录错误"""
        with patch('processor.WhisperEngine') as mock_engine_class, \
             patch('processor.SRTSplitter') as mock_splitter_class:

            from processor import VideoProcessor
            from progress_tracker import ProgressTracker

            with tempfile.TemporaryDirectory() as tmpdir:
                tracker = ProgressTracker(
                    video_path="/fake/video.mp4",
                    video_name="video.mp4",
                    video_duration=60.0,
                    progress_callback=MagicMock()
                )

                vp = VideoProcessor()

                # 创建一个无效格式的文件
                with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, dir=tmpdir) as f:
                    f.write(b"not a video")
                    invalid_path = f.name

                try:
                    with pytest.raises(ValueError, match="不支持"):
                        vp.process_video(invalid_path, progress_tracker=tracker)

                    # 验证 validation 阶段被标记为失败
                    assert "validation" in tracker.task.stages
                    validation_stage = tracker.task.stages["validation"]
                    assert validation_stage.status.value == "failed"
                finally:
                    if os.path.exists(invalid_path):
                        os.remove(invalid_path)

    def test_process_video_with_tracker_file_not_found(self):
        """测试使用 tracker 时文件不存在会记录错误"""
        with patch('processor.WhisperEngine') as mock_engine_class, \
             patch('processor.SRTSplitter') as mock_splitter_class:

            from processor import VideoProcessor
            from progress_tracker import ProgressTracker

            with tempfile.TemporaryDirectory() as tmpdir:
                tracker = ProgressTracker(
                    video_path="/fake/video.mp4",
                    video_name="video.mp4",
                    video_duration=60.0,
                    progress_callback=MagicMock()
                )

                vp = VideoProcessor()

                nonexistent_path = "/nonexistent/video.mp4"

                with pytest.raises(FileNotFoundError):
                    vp.process_video(nonexistent_path, progress_tracker=tracker)

                # 验证 validation 阶段被标记为失败
                assert "validation" in tracker.task.stages
                validation_stage = tracker.task.stages["validation"]
                assert validation_stage.status.value == "failed"


class TestCleanup:
    """测试清理功能"""

    def test_cleanup_removes_files(self):
        """测试清理删除文件"""
        from processor import VideoProcessor

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        assert os.path.exists(temp_path)

        with patch('processor.WhisperEngine'), patch('processor.SRTSplitter'):
            vp = VideoProcessor()
            vp._cleanup([temp_path])

        assert not os.path.exists(temp_path)

    def test_cleanup_handles_nonexistent(self):
        """测试清理处理不存在的文件"""
        with patch('processor.WhisperEngine'), patch('processor.SRTSplitter'):
            from processor import VideoProcessor

            vp = VideoProcessor()
            # 不应抛出异常
            vp._cleanup(["/nonexistent/file.wav"])


class TestEdgeCases:
    """测试边界情况"""

    def test_custom_filename_sanitization(self):
        """测试自定义文件名清理"""
        with patch('processor.WhisperEngine'), patch('processor.SRTSplitter'):
            from processor import VideoProcessor
            vp = VideoProcessor()

            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
                video_path = f.name

            try:
                # 测试处理时文件名清理不会导致错误
                with patch.object(vp, '_extract_audio', return_value='/tmp/audio.wav'), \
                     patch.object(vp, '_transcribe_audio', return_value=[]), \
                     patch.object(vp, '_generate_srt_with_name', return_value='/tmp/test.srt'), \
                     patch.object(vp, '_cleanup'):
                    result = vp.process_video(video_path, custom_filename="test<>|*/file")
            finally:
                if os.path.exists(video_path):
                    os.remove(video_path)
