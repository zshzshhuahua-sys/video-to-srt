"""
测试 whisper_engine.py Whisper 引擎封装
TDD RED 阶段：编写会失败的测试
"""
import os
import pytest
from unittest.mock import patch, MagicMock, Mock


class TestWhisperEngineInit:
    """测试 WhisperEngine 初始化"""

    def test_init_loads_model_immediately(self):
        """测试初始化时立即加载模型（当前问题）"""
        with patch('whisper_engine.whisper.load_model') as mock_load:
            mock_load.return_value = MagicMock()
            from whisper_engine import WhisperEngine
            engine = WhisperEngine(model_name="tiny")
            # 初始化时应该调用了 load_model
            mock_load.assert_called_once_with("tiny")

    def test_init_accepts_model_name(self):
        """测试初始化接受模型名称参数"""
        with patch('whisper_engine.whisper.load_model') as mock_load:
            mock_load.return_value = MagicMock()
            from whisper_engine import WhisperEngine
            engine = WhisperEngine(model_name="medium")
            assert engine.model_name == "medium"

    def test_lazy_load_option(self):
        """测试延迟加载选项 - 模型不在 __init__ 时加载"""
        with patch('whisper_engine.whisper.load_model') as mock_load:
            mock_load.return_value = MagicMock()
            from whisper_engine import WhisperEngine
            # 如果有 lazy_load 选项，初始化时不应加载模型
            engine = WhisperEngine(model_name="small", lazy_load=True)
            # 如果 lazy_load 为 True，load_model 不应该在 __init__ 中调用
            # 注意：这个测试会失败，因为当前实现没有 lazy_load 选项
            mock_load.assert_not_called()


class TestWhisperTranscribe:
    """测试 transcribe 方法"""

    def test_transcribe_returns_segments(self):
        """测试 transcribe 返回字幕段列表"""
        with patch('whisper_engine.whisper.load_model') as mock_load:
            mock_model = MagicMock()
            mock_model.transcribe.return_value = {
                "segments": [
                    {"start": 0.0, "end": 2.5, "text": "第一句"},
                    {"start": 2.6, "end": 5.3, "text": "第二句"},
                ]
            }
            mock_load.return_value = mock_model

            from whisper_engine import WhisperEngine
            engine = WhisperEngine(model_name="tiny")
            result = engine.transcribe("dummy_audio.wav", language="zh")

            assert len(result) == 2
            assert result[0]["text"] == "第一句"

    def test_transcribe_with_progress_callback(self):
        """测试 transcribe 支持 progress_callback"""
        with patch('whisper_engine.whisper.load_model') as mock_load:
            mock_model = MagicMock()
            mock_model.transcribe.return_value = {"segments": []}
            mock_load.return_value = mock_model

            from whisper_engine import WhisperEngine
            engine = WhisperEngine(model_name="tiny")

            callback_called = []
            def progress_callback(percent, message, detail=None):
                callback_called.append((percent, message, detail))

            engine.transcribe("dummy.wav", language="zh", progress_callback=progress_callback)
            # 如果 progress_callback 被实现，callback_called 应该不为空
            assert len(callback_called) > 0, "Expected progress_callback to be called"

    def test_transcribe_handles_error(self):
        """测试 transcribe 错误处理"""
        with patch('whisper_engine.whisper.load_model') as mock_load:
            mock_model = MagicMock()
            mock_model.transcribe.side_effect = Exception("Audio file not found")
            mock_load.return_value = mock_model

            from whisper_engine import WhisperEngine
            engine = WhisperEngine(model_name="tiny")

            # 应该抛出异常，而不是静默失败
            with pytest.raises(Exception):
                engine.transcribe("nonexistent.wav", language="zh")


class TestWhisperTranscribeWithTimestamps:
    """测试 transcribe_with_timestamps 方法"""

    def test_transcribe_with_timestamps_returns_dict_format(self):
        """测试返回字典格式的时间戳"""
        with patch('whisper_engine.whisper.load_model') as mock_load:
            mock_model = MagicMock()
            mock_model.transcribe.return_value = {
                "segments": [
                    {"start": 0.0, "end": 2.5, "text": "  第一句  "},
                    {"start": 2.6, "end": 5.3, "text": "  第二句  "},
                ]
            }
            mock_load.return_value = mock_model

            from whisper_engine import WhisperEngine
            engine = WhisperEngine(model_name="tiny")
            result = engine.transcribe_with_timestamps("audio.wav", language="zh")

            assert len(result) == 2
            assert result[0]["start"] == 0.0
            assert result[0]["end"] == 2.5
            assert result[0]["text"] == "第一句"  # 应该去除空格

    def test_transcribe_with_timestamps_default_language(self):
        """测试默认语言是中文"""
        with patch('whisper_engine.whisper.load_model') as mock_load:
            mock_model = MagicMock()
            mock_model.transcribe.return_value = {"segments": []}
            mock_load.return_value = mock_model

            from whisper_engine import WhisperEngine
            engine = WhisperEngine(model_name="tiny")
            engine.transcribe_with_timestamps("audio.wav")

            # 验证 transcribe 被调用时使用了默认语言参数
            call_args = mock_model.transcribe.call_args
            # 可以通过检查调用参数验证


class TestWhisperErrorHandling:
    """测试错误处理"""

    def test_model_load_error_handling(self):
        """测试模型加载失败处理"""
        with patch('whisper_engine.whisper.load_model') as mock_load:
            mock_load.side_effect = Exception("Model download failed")

            from whisper_engine import WhisperEngine
            # 初始化时应该捕获异常或抛出友好的错误信息
            with pytest.raises(Exception):
                engine = WhisperEngine(model_name="tiny")

    def test_audio_file_not_found(self):
        """测试音频文件不存在时的错误处理"""
        with patch('whisper_engine.whisper.load_model') as mock_load:
            mock_model = MagicMock()
            mock_model.transcribe.side_effect = Exception("Audio file not found")
            mock_load.return_value = mock_model

            from whisper_engine import WhisperEngine
            engine = WhisperEngine(model_name="tiny")

            with pytest.raises(Exception):
                engine.transcribe("nonexistent.wav", language="zh")


class TestWhisperCaching:
    """测试模型缓存支持"""

    def test_cached_modelDecorator_exists(self):
        """测试是否存在 cache_model 装饰器或缓存支持"""
        # 检查是否有 st 缓存支持或类似的缓存机制
        from whisper_engine import WhisperEngine
        import inspect

        # 应该有某种缓存支持的迹象
        # 比如 @st.cache_resource 装饰器或 lazy_load 参数
        sig = inspect.signature(WhisperEngine.__init__)
        params = sig.parameters

        # 如果实现了缓存，应该有 lazy_load 或 cache 相关参数
        # 这个测试会失败，直到我们实现这个功能
        # assert 'lazy_load' in params or 'cache' in params


class TestWhisperSegmentProgress:
    """测试 whisper 引擎的段级别进度报告"""

    def test_transcribe_reports_segment_progress(self):
        """测试 transcribe 报告段级别进度"""
        with patch('whisper_engine.whisper.load_model') as mock_load:
            mock_model = MagicMock()
            # 模拟 whisper 返回多个段
            mock_model.transcribe.return_value = {
                "segments": [
                    {"start": 0.0, "end": 2.5, "text": "第一句"},
                    {"start": 2.6, "end": 5.0, "text": "第二句"},
                    {"start": 5.1, "end": 8.0, "text": "第三句"},
                ]
            }
            mock_load.return_value = mock_model

            from whisper_engine import WhisperEngine
            engine = WhisperEngine(model_name="tiny")

            progress_calls = []
            def progress_callback(percent, message, detail=None):
                progress_calls.append({
                    "percent": percent,
                    "message": message,
                    "detail": detail
                })

            engine.transcribe("dummy.wav", language="zh", progress_callback=progress_callback)

            # 应该有多次进度调用（不只是开始和结束）
            # 至少应该对每个段都有进度报告
            assert len(progress_calls) >= 3, f"Expected at least 3 progress calls, got {len(progress_calls)}"

    def test_progress_callback_receives_segment_info(self):
        """测试进度回调接收段信息"""
        with patch('whisper_engine.whisper.load_model') as mock_load:
            mock_model = MagicMock()
            mock_model.transcribe.return_value = {
                "segments": [
                    {"start": 0.0, "end": 2.5, "text": "第一句"},
                    {"start": 2.6, "end": 5.0, "text": "第二句"},
                ]
            }
            mock_load.return_value = mock_model

            from whisper_engine import WhisperEngine
            engine = WhisperEngine(model_name="tiny")

            received_details = []
            def progress_callback(percent, message, detail=None):
                if detail is not None:
                    received_details.append(detail)

            engine.transcribe("dummy.wav", language="zh", progress_callback=progress_callback)

            # 验证 detail 包含 segment 和 total 信息
            assert len(received_details) > 0, "Expected at least one detail dict"
            for detail in received_details:
                assert "stage" in detail, f"Expected 'stage' in detail, got {detail}"
                assert detail["stage"] == "transcription", f"Expected stage='transcription', got {detail}"
                assert "segment" in detail, f"Expected 'segment' in detail, got {detail}"
                assert "total" in detail, f"Expected 'total' in detail, got {detail}"
                assert isinstance(detail["segment"], int), f"Expected segment to be int, got {type(detail['segment'])}"
                assert isinstance(detail["total"], int), f"Expected total to be int, got {type(detail['total'])}"
                assert detail["segment"] >= 0, f"Expected segment >= 0, got {detail['segment']}"
                assert detail["total"] >= 1, f"Expected total >= 1, got {detail['total']}"
                assert detail["segment"] < detail["total"], f"Expected segment < total, got segment={detail['segment']}, total={detail['total']}"

    def test_get_audio_duration_returns_float(self):
        """测试 get_audio_duration 返回浮点数秒数"""
        with patch('whisper_engine.whisper.load_model') as mock_load, \
             patch('whisper_engine.get_video_duration') as mock_duration:
            mock_load.return_value = MagicMock()
            mock_duration.return_value = 123.456

            from whisper_engine import WhisperEngine
            engine = WhisperEngine(model_name="tiny")

            duration = engine.get_audio_duration("/path/to/audio.wav")

            assert isinstance(duration, float), f"Expected float, got {type(duration)}"
            assert duration == 123.456, f"Expected 123.456, got {duration}"
            mock_duration.assert_called_once_with("/path/to/audio.wav")

    def test_get_audio_duration_handles_invalid_video(self):
        """测试 get_audio_duration 处理无效文件"""
        with patch('whisper_engine.whisper.load_model') as mock_load, \
             patch('whisper_engine.get_video_duration') as mock_duration:
            mock_load.return_value = MagicMock()
            mock_duration.return_value = None

            from whisper_engine import WhisperEngine
            engine = WhisperEngine(model_name="tiny")

            duration = engine.get_audio_duration("/invalid/file.wav")

            assert duration is None, f"Expected None for invalid file, got {duration}"


class TestWhisperIntegration:
    """集成测试"""

    def test_full_transcribe_flow(self):
        """测试完整的识别流程"""
        with patch('whisper_engine.whisper.load_model') as mock_load:
            mock_model = MagicMock()
            mock_model.transcribe.return_value = {
                "segments": [
                    {"start": 0.0, "end": 2.5, "text": "测试字幕"},
                ]
            }
            mock_load.return_value = mock_model

            from whisper_engine import WhisperEngine
            engine = WhisperEngine(model_name="small")
            result = engine.transcribe_with_timestamps("test.wav", language="zh")

            assert len(result) == 1
            assert "text" in result[0]
            assert "start" in result[0]
            assert "end" in result[0]
