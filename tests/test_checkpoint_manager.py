"""
测试 checkpoint_manager.py 断点管理器
TDD RED 阶段：编写会失败的测试
"""
import pytest
import tempfile
import os
import json
import time
from unittest.mock import patch, MagicMock


class TestCheckpointManager:
    """测试断点管理器"""

    def test_save_checkpoint_creates_file(self):
        """测试保存断点创建文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from checkpoint_manager import CheckpointManager, Checkpoint

            cm = CheckpointManager(checkpoint_dir=tmpdir)
            checkpoint = Checkpoint(
                video_path="/path/to/video.mp4",
                video_name="video.mp4",
                audio_path="/path/to/audio.wav",
                processed_segments=[{"start": 0.0, "end": 2.5, "text": "测试"}],
                last_segment_index=0,
                stage="transcription"
            )

            cm.save_checkpoint(checkpoint)

            # 验证文件被创建
            path = cm._get_checkpoint_path("video.mp4")
            assert os.path.exists(path), "Checkpoint file should be created"

    def test_load_checkpoint_returns_checkpoint(self):
        """测试加载断点返回 Checkpoint 对象"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from checkpoint_manager import CheckpointManager, Checkpoint

            cm = CheckpointManager(checkpoint_dir=tmpdir)

            # 先保存一个断点
            original = Checkpoint(
                video_path="/path/to/video.mp4",
                video_name="video.mp4",
                audio_path="/path/to/audio.wav",
                processed_segments=[{"start": 0.0, "end": 2.5, "text": "测试"}],
                last_segment_index=0,
                stage="transcription"
            )
            cm.save_checkpoint(original)

            # 加载断点
            loaded = cm.load_checkpoint("video.mp4")

            assert loaded is not None, "Loaded checkpoint should not be None"
            assert isinstance(loaded, Checkpoint), "Loaded should be Checkpoint instance"
            assert loaded.video_name == "video.mp4"
            assert loaded.audio_path == "/path/to/audio.wav"
            assert loaded.last_segment_index == 0
            assert loaded.stage == "transcription"
            assert len(loaded.processed_segments) == 1

    def test_load_checkpoint_returns_none_if_not_exists(self):
        """测试加载不存在的断点返回 None"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from checkpoint_manager import CheckpointManager

            cm = CheckpointManager(checkpoint_dir=tmpdir)

            result = cm.load_checkpoint("nonexistent_video.mp4")

            assert result is None, "Should return None for nonexistent checkpoint"

    def test_has_checkpoint_returns_true_when_exists(self):
        """测试有断点时返回 True"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from checkpoint_manager import CheckpointManager, Checkpoint

            cm = CheckpointManager(checkpoint_dir=tmpdir)

            # 保存一个有有效 last_segment_index 的断点
            checkpoint = Checkpoint(
                video_path="/path/to/video.mp4",
                video_name="video.mp4",
                last_segment_index=5,  # >= 0 表示有效的断点
                stage="transcription"
            )
            cm.save_checkpoint(checkpoint)

            assert cm.has_checkpoint("video.mp4") is True

    def test_has_checkpoint_returns_false_when_not_exists(self):
        """测试没有断点时返回 False"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from checkpoint_manager import CheckpointManager

            cm = CheckpointManager(checkpoint_dir=tmpdir)

            assert cm.has_checkpoint("nonexistent_video.mp4") is False

    def test_delete_checkpoint_removes_file(self):
        """测试删除断点移除文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from checkpoint_manager import CheckpointManager, Checkpoint

            cm = CheckpointManager(checkpoint_dir=tmpdir)

            # 先保存一个断点
            checkpoint = Checkpoint(
                video_path="/path/to/video.mp4",
                video_name="video.mp4",
                last_segment_index=0,
                stage="transcription"
            )
            cm.save_checkpoint(checkpoint)

            # 验证文件存在
            path = cm._get_checkpoint_path("video.mp4")
            assert os.path.exists(path)

            # 删除断点
            cm.delete_checkpoint("video.mp4")

            # 验证文件被删除
            assert not os.path.exists(path), "Checkpoint file should be deleted"

    def test_checkpoint_file_contains_required_fields(self):
        """测试断点文件包含必需字段"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from checkpoint_manager import CheckpointManager, Checkpoint

            cm = CheckpointManager(checkpoint_dir=tmpdir)

            checkpoint = Checkpoint(
                video_path="/path/to/video.mp4",
                video_name="video.mp4",
                audio_path="/path/to/audio.wav",
                processed_segments=[{"start": 0.0, "end": 2.5, "text": "第一句"}],
                last_segment_index=0,
                stage="transcription"
            )
            cm.save_checkpoint(checkpoint)

            # 读取文件内容
            path = cm._get_checkpoint_path("video.mp4")
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 验证必需字段
            required_fields = [
                "video_path", "video_name", "audio_path", "processed_segments",
                "last_segment_index", "stage", "created_at", "updated_at"
            ]
            for field in required_fields:
                assert field in data, f"Required field '{field}' should be in checkpoint file"

            # 验证数据类型
            assert isinstance(data["processed_segments"], list)
            assert isinstance(data["last_segment_index"], int)
            assert isinstance(data["stage"], str)


class TestCheckpointDataClass:
    """测试 Checkpoint 数据类"""

    def test_checkpoint_to_dict(self):
        """测试 Checkpoint 转换为字典"""
        from checkpoint_manager import Checkpoint

        checkpoint = Checkpoint(
            video_path="/path/to/video.mp4",
            video_name="video.mp4",
            audio_path="/path/to/audio.wav",
            processed_segments=[{"start": 0.0, "end": 2.5, "text": "测试"}],
            last_segment_index=5,
            stage="transcription"
        )

        data = checkpoint.to_dict()

        assert data["video_path"] == "/path/to/video.mp4"
        assert data["video_name"] == "video.mp4"
        assert data["last_segment_index"] == 5
        assert data["stage"] == "transcription"
        assert len(data["processed_segments"]) == 1

    def test_checkpoint_from_dict(self):
        """测试从字典创建 Checkpoint"""
        from checkpoint_manager import Checkpoint

        data = {
            "video_path": "/path/to/video.mp4",
            "video_name": "video.mp4",
            "audio_path": "/path/to/audio.wav",
            "processed_segments": [{"start": 0.0, "end": 2.5, "text": "测试"}],
            "last_segment_index": 5,
            "stage": "transcription",
            "created_at": 1234567890.0,
            "updated_at": 1234567891.0
        }

        checkpoint = Checkpoint.from_dict(data)

        assert checkpoint.video_path == "/path/to/video.mp4"
        assert checkpoint.video_name == "video.mp4"
        assert checkpoint.last_segment_index == 5
        assert checkpoint.stage == "transcription"
        assert len(checkpoint.processed_segments) == 1

    def test_checkpoint_default_values(self):
        """测试 Checkpoint 默认值"""
        from checkpoint_manager import Checkpoint

        checkpoint = Checkpoint(
            video_path="/path/to/video.mp4",
            video_name="video.mp4"
        )

        assert checkpoint.audio_path == ""
        assert checkpoint.processed_segments == []
        assert checkpoint.last_segment_index == -1
        assert checkpoint.stage == "idle"
        assert checkpoint.created_at > 0
        assert checkpoint.updated_at > 0


class TestCheckpointManagerEdgeCases:
    """测试断点管理器边界情况"""

    def test_checkpoint_with_special_characters_in_name(self):
        """测试文件名包含特殊字符"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from checkpoint_manager import CheckpointManager, Checkpoint

            cm = CheckpointManager(checkpoint_dir=tmpdir)

            # 特殊字符文件名
            checkpoint = Checkpoint(
                video_path="/path/to/video.mp4",
                video_name="video_with spaces & symbols!.mp4",
                last_segment_index=0,
                stage="transcription"
            )

            # 保存和加载不应该抛出异常
            cm.save_checkpoint(checkpoint)
            loaded = cm.load_checkpoint("video_with spaces & symbols!.mp4")

            assert loaded is not None
            assert loaded.video_name == "video_with spaces & symbols!.mp4"

    def test_checkpoint_handles_invalid_json(self):
        """测试处理无效 JSON 文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from checkpoint_manager import CheckpointManager

            cm = CheckpointManager(checkpoint_dir=tmpdir)

            # 创建无效的 JSON 文件
            path = cm._get_checkpoint_path("bad_video.mp4")
            with open(path, "w") as f:
                f.write("not valid json {")

            # 应该返回 None 而不是抛出异常
            result = cm.load_checkpoint("bad_video.mp4")
            assert result is None

    def test_checkpoint_handles_empty_file(self):
        """测试处理空文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from checkpoint_manager import CheckpointManager

            cm = CheckpointManager(checkpoint_dir=tmpdir)

            # 创建空文件
            path = cm._get_checkpoint_path("empty_video.mp4")
            with open(path, "w") as f:
                f.write("")

            # 应该返回 None 而不是抛出异常
            result = cm.load_checkpoint("empty_video.mp4")
            assert result is None
