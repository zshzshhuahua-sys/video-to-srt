"""
测试 app.py UI 组件
TDD RED 阶段：编写会失败的测试
"""
import pytest
from unittest.mock import patch, MagicMock


class TestProgressBarUI:
    """测试进度条 UI 组件"""

    def test_progress_bar_accepts_percent(self):
        """测试进度条接受百分比参数"""
        with patch('app.st') as mock_st:
            from app import _render_progress

            # 模拟进度数据
            task_data = MagicMock()
            task_data.overall_progress_percent = 50
            task_data.stages = {}

            # 调用 _render_progress
            _render_progress(task_data, None)

            # 验证 st.progress 被调用
            mock_st.progress.assert_called_once()
            call_args = mock_st.progress.call_args
            assert call_args[0][0] == 0.5  # 50% = 0.5

    def test_eta_display_format(self):
        """测试 ETA 显示格式"""
        from app import _format_eta

        # 测试各种 ETA 值
        assert _format_eta(0) == "0:00"
        assert _format_eta(30) == "0:30"
        assert _format_eta(60) == "1:00"
        assert _format_eta(90) == "1:30"
        assert _format_eta(3661) == "1:01:01"
        assert _format_eta(None) == "--:--"  # None case

    def test_render_progress_with_stages(self):
        """测试带阶段详情的进度渲染"""
        with patch('app.st') as mock_st:
            from app import _render_progress
            from progress_state import StageProgress, ProcessingStatus

            # 模拟任务数据
            task_data = MagicMock()
            task_data.overall_progress_percent = 50
            task_data.stages = {
                "audio_extraction": StageProgress(
                    name="audio_extraction",
                    status=ProcessingStatus.COMPLETED,
                    percent=100,
                    message="完成"
                ),
                "transcription": StageProgress(
                    name="transcription",
                    status=ProcessingStatus.PROCESSING,
                    percent=50,
                    message="正在识别..."
                )
            }

            _render_progress(task_data, None)

            # 验证 st.progress 被调用
            mock_st.progress.assert_called_once()


class TestErrorPanelUI:
    """测试错误面板 UI 组件"""

    def test_error_panel_shows_suggestion(self):
        """测试错误面板显示建议"""
        with patch('app.st') as mock_st:
            from app import _render_error
            from exceptions import AudioExtractionError, ProcessingStage, ErrorSeverity

            # 创建一个带有建议的错误
            error = AudioExtractionError(
                message="ffmpeg not found",
                suggestion="Install ffmpeg: brew install ffmpeg"
            )

            _render_error(error)

            # 验证 st.error 或 st.warning 被调用
            # 错误应该被显示
            assert mock_st.error.called or mock_st.warning.called

    def test_render_error_with_no_suggestion(self):
        """测试没有建议时错误仍能显示"""
        with patch('app.st') as mock_st:
            from app import _render_error
            from exceptions import AudioExtractionError

            # 创建一个没有建议的错误
            error = AudioExtractionError(message="Some error")

            _render_error(error)

            # 验证 st.error 被调用
            assert mock_st.error.called
