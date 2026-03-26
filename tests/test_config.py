"""
测试 config.py 配置模块
TDD RED 阶段：编写会失败的测试
"""
import os
import pytest
from unittest.mock import patch


class TestConfigDefaults:
    """测试默认配置值"""

    def test_whisper_model_default(self):
        """测试默认 WHISPER_MODEL 是 small"""
        # 先设置可能存在的环境变量为空
        with patch.dict(os.environ, {}, clear=True):
            # 重新导入以获取干净的状态
            import importlib
            import sys
            # 清除已导入的模块
            for mod in list(sys.modules.keys()):
                if mod == 'config':
                    del sys.modules[mod]
            from config import WHISPER_MODEL
            assert WHISPER_MODEL == "small"

    def test_max_file_size_default(self):
        """测试默认 MAX_FILE_SIZE 是 10GB"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import sys
            for mod in list(sys.modules.keys()):
                if mod == 'config':
                    del sys.modules[mod]
            from config import MAX_FILE_SIZE
            assert MAX_FILE_SIZE == 10 * 1024**3

    def test_audio_sample_rate_default(self):
        """测试默认 AUDIO_SAMPLE_RATE 是 16000"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import sys
            for mod in list(sys.modules.keys()):
                if mod == 'config':
                    del sys.modules[mod]
            from config import AUDIO_SAMPLE_RATE
            assert AUDIO_SAMPLE_RATE == 16000

    def test_segment_duration_default(self):
        """测试默认 SEGMENT_DURATION 是 30 分钟（1800 秒）"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import sys
            for mod in list(sys.modules.keys()):
                if mod == 'config':
                    del sys.modules[mod]
            from config import SEGMENT_DURATION
            assert SEGMENT_DURATION == 30 * 60

    def test_srt_split_size_default(self):
        """测试默认 SRT_SPLIT_SIZE 是 10MB"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import sys
            for mod in list(sys.modules.keys()):
                if mod == 'config':
                    del sys.modules[mod]
            from config import SRT_SPLIT_SIZE
            assert SRT_SPLIT_SIZE == 10 * 1024**2

    def test_supported_formats_default(self):
        """测试默认 SUPPORTED_FORMATS 包含必要的格式"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import sys
            for mod in list(sys.modules.keys()):
                if mod == 'config':
                    del sys.modules[mod]
            from config import SUPPORTED_FORMATS
            assert "mp4" in SUPPORTED_FORMATS
            assert "avi" in SUPPORTED_FORMATS
            assert "mkv" in SUPPORTED_FORMATS
            assert "mov" in SUPPORTED_FORMATS
            assert "webm" in SUPPORTED_FORMATS


class TestConfigEnvOverride:
    """测试环境变量覆盖功能"""

    def test_whisper_model_env_override(self):
        """测试 WHISPER_MODEL 可通过环境变量覆盖"""
        env_vars = {"WHISPER_MODEL": "medium"}
        with patch.dict(os.environ, env_vars, clear=True):
            import importlib
            import sys
            for mod in list(sys.modules.keys()):
                if mod == 'config':
                    del sys.modules[mod]
            from config import WHISPER_MODEL
            assert WHISPER_MODEL == "medium"

    def test_max_file_size_env_override(self):
        """测试 MAX_FILE_SIZE 可通过环境变量覆盖"""
        env_vars = {"MAX_FILE_SIZE": "5368709120"}  # 5GB
        with patch.dict(os.environ, env_vars, clear=True):
            import importlib
            import sys
            for mod in list(sys.modules.keys()):
                if mod == 'config':
                    del sys.modules[mod]
            from config import MAX_FILE_SIZE
            assert MAX_FILE_SIZE == 5 * 1024**3

    def test_audio_sample_rate_env_override(self):
        """测试 AUDIO_SAMPLE_RATE 可通过环境变量覆盖"""
        env_vars = {"AUDIO_SAMPLE_RATE": "44100"}
        with patch.dict(os.environ, env_vars, clear=True):
            import importlib
            import sys
            for mod in list(sys.modules.keys()):
                if mod == 'config':
                    del sys.modules[mod]
            from config import AUDIO_SAMPLE_RATE
            assert AUDIO_SAMPLE_RATE == 44100

    def test_segment_duration_env_override(self):
        """测试 SEGMENT_DURATION 可通过环境变量覆盖"""
        env_vars = {"SEGMENT_DURATION": "600"}  # 10分钟
        with patch.dict(os.environ, env_vars, clear=True):
            import importlib
            import sys
            for mod in list(sys.modules.keys()):
                if mod == 'config':
                    del sys.modules[mod]
            from config import SEGMENT_DURATION
            assert SEGMENT_DURATION == 600

    def test_srt_split_size_env_override(self):
        """测试 SRT_SPLIT_SIZE 可通过环境变量覆盖"""
        env_vars = {"SRT_SPLIT_SIZE": "20971520"}  # 20MB
        with patch.dict(os.environ, env_vars, clear=True):
            import importlib
            import sys
            for mod in list(sys.modules.keys()):
                if mod == 'config':
                    del sys.modules[mod]
            from config import SRT_SPLIT_SIZE
            assert SRT_SPLIT_SIZE == 20 * 1024**2

    def test_supported_formats_env_override(self):
        """测试 SUPPORTED_FORMATS 可通过环境变量覆盖"""
        env_vars = {"SUPPORTED_FORMATS": "mp4,mkv,flv"}
        with patch.dict(os.environ, env_vars, clear=True):
            import importlib
            import sys
            for mod in list(sys.modules.keys()):
                if mod == 'config':
                    del sys.modules[mod]
            from config import SUPPORTED_FORMATS
            assert SUPPORTED_FORMATS == ["mp4", "mkv", "flv"]


class TestConfigTypes:
    """测试配置类型正确性"""

    def test_whisper_model_is_string(self):
        """测试 WHISPER_MODEL 是字符串类型"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import sys
            for mod in list(sys.modules.keys()):
                if mod == 'config':
                    del sys.modules[mod]
            from config import WHISPER_MODEL
            assert isinstance(WHISPER_MODEL, str)

    def test_max_file_size_is_int(self):
        """测试 MAX_FILE_SIZE 是整数类型"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import sys
            for mod in list(sys.modules.keys()):
                if mod == 'config':
                    del sys.modules[mod]
            from config import MAX_FILE_SIZE
            assert isinstance(MAX_FILE_SIZE, int)

    def test_audio_sample_rate_is_int(self):
        """测试 AUDIO_SAMPLE_RATE 是整数类型"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import sys
            for mod in list(sys.modules.keys()):
                if mod == 'config':
                    del sys.modules[mod]
            from config import AUDIO_SAMPLE_RATE
            assert isinstance(AUDIO_SAMPLE_RATE, int)

    def test_supported_formats_is_list(self):
        """测试 SUPPORTED_FORMATS 是列表类型"""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import sys
            for mod in list(sys.modules.keys()):
                if mod == 'config':
                    del sys.modules[mod]
            from config import SUPPORTED_FORMATS
            assert isinstance(SUPPORTED_FORMATS, list)
