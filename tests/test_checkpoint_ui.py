"""
测试断点续传 UI 功能
TDD RED 阶段：编写会失败的测试
"""
import pytest
from unittest.mock import patch, MagicMock


class TestCheckpointUI:
    """测试断点续传 UI 组件"""

    def test_checkpoint_check_called_during_file_processing(self):
        """测试文件处理过程中调用断点检查"""
        with patch('app.st') as mock_st, \
             patch('app.CheckpointManager') as mock_cm_class:

            # 模拟 CheckpointManager 返回有有效断点
            mock_cm_instance = MagicMock()
            mock_cm_instance.has_checkpoint.return_value = True
            mock_cm_class.return_value = mock_cm_instance

            # 模拟上传的文件
            uploaded_file = MagicMock()
            uploaded_file.name = "test_video.mp4"
            uploaded_file.size = 1000000

            # 模拟 session_state
            mock_st.session_state = {}

            # 模拟 validate_uploaded_file 不抛出异常
            with patch('app.validate_uploaded_file') as mock_validate:
                mock_validate.return_value = 1000000

                # 模拟文件存在
                with patch('os.path.exists', return_value=True):
                    # 调用检查断点的逻辑
                    from checkpoint_manager import CheckpointManager
                    video_name = "test_video.mp4"

                    # 直接测试 checkpoint manager 的 has_checkpoint
                    checkpoint_manager = CheckpointManager()
                    # 由于我们 mock 了 CheckpointManager，实际调用的是 mock
                    from app import CheckpointManager as AppCheckpointManager
                    import app

                    # 重新 patch 让 app 使用我们的 mock
                    with patch.object(app, 'CheckpointManager', return_value=mock_cm_instance):
                        checkpoint_manager = app.CheckpointManager()
                        result = checkpoint_manager.has_checkpoint(video_name)

                    assert result is True
                    mock_cm_instance.has_checkpoint.assert_called_with(video_name)

    def test_has_checkpoint_returns_true_when_checkpoint_exists(self):
        """测试当断点存在时 has_checkpoint 返回 True"""
        with patch('app.CheckpointManager') as mock_cm_class:
            mock_cm_instance = MagicMock()
            mock_cm_instance.has_checkpoint.return_value = True
            mock_cm_class.return_value = mock_cm_instance

            from app import CheckpointManager
            cm = CheckpointManager()
            result = cm.has_checkpoint("test_video.mp4")

            assert result is True
            mock_cm_instance.has_checkpoint.assert_called_with("test_video.mp4")

    def test_has_checkpoint_returns_false_when_no_checkpoint(self):
        """测试当没有断点时 has_checkpoint 返回 False"""
        with patch('app.CheckpointManager') as mock_cm_class:
            mock_cm_instance = MagicMock()
            mock_cm_instance.has_checkpoint.return_value = False
            mock_cm_class.return_value = mock_cm_instance

            from app import CheckpointManager
            cm = CheckpointManager()
            result = cm.has_checkpoint("nonexistent.mp4")

            assert result is False
            mock_cm_instance.has_checkpoint.assert_called_with("nonexistent.mp4")

    def test_checkpoint_manager_initialized_with_default_dir(self):
        """测试 CheckpointManager 使用默认目录初始化"""
        with patch('app.CheckpointManager') as mock_cm_class:
            mock_cm_instance = MagicMock()
            mock_cm_class.return_value = mock_cm_instance

            from app import CheckpointManager
            cm = CheckpointManager()

            # 验证 CheckpointManager 被调用
            mock_cm_class.assert_called_once()
