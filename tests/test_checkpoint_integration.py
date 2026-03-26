"""
测试断点续传与 processor.py 的集成
TDD RED 阶段：编写会失败的测试
"""
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock


class TestProcessorCheckpoint:
    """测试处理器的断点续传功能"""

    def test_process_video_saves_checkpoint_on_segment_complete(self):
        """测试处理视频时在片段完成后保存断点"""
        with patch('processor.WhisperEngine') as mock_engine_class, \
             patch('processor.SRTSplitter') as mock_splitter_class, \
             patch('processor.CheckpointManager') as mock_cm_class:

            mock_engine = MagicMock()
            mock_engine.transcribe_with_timestamps.return_value = [
                {"start": 0.0, "end": 2.5, "text": "第一句"},
                {"start": 2.6, "end": 5.0, "text": "第二句"},
            ]
            mock_engine_class.return_value = mock_engine

            mock_splitter = MagicMock()
            mock_splitter.split_if_needed.return_value = ["/tmp/test.srt"]
            mock_splitter_class.return_value = mock_splitter

            mock_cm_instance = MagicMock()
            # 确保 has_checkpoint 返回 False，这样不会进入断点恢复逻辑
            mock_cm_instance.has_checkpoint.return_value = False
            mock_cm_class.return_value = mock_cm_instance

            from processor import VideoProcessor
            from checkpoint_manager import Checkpoint, CheckpointManager

            vp = VideoProcessor()

            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
                video_path = f.name

            try:
                with patch.object(vp, '_extract_audio', return_value='/tmp/audio.wav'), \
                     patch.object(vp, '_cleanup'):
                    vp.process_video(video_path, progress_tracker=None)

                # 验证 CheckpointManager.save_checkpoint 被调用
                assert mock_cm_instance.save_checkpoint.called, \
                    "save_checkpoint should be called after processing"

                # 验证保存的 checkpoint 包含正确的视频名称
                saved_checkpoint = mock_cm_instance.save_checkpoint.call_args[0][0]
                assert saved_checkpoint.video_name in video_path or saved_checkpoint.video_path == video_path
            finally:
                if os.path.exists(video_path):
                    os.remove(video_path)

    def test_process_video_loads_checkpoint_if_exists(self):
        """测试处理视频时加载已存在的断点"""
        from checkpoint_manager import Checkpoint

        with patch('processor.WhisperEngine') as mock_engine_class, \
             patch('processor.SRTSplitter') as mock_splitter_class, \
             patch('processor.CheckpointManager') as mock_cm_class:

            mock_engine = MagicMock()
            mock_engine.transcribe_with_timestamps.return_value = []
            mock_engine_class.return_value = mock_engine

            mock_splitter = MagicMock()
            mock_splitter.split_if_needed.return_value = ["/tmp/test.srt"]
            mock_splitter_class.return_value = mock_splitter

            mock_cm_instance = MagicMock()
            # 模拟有断点存在
            mock_cm_instance.has_checkpoint.return_value = True
            # load_checkpoint 需要返回一个有效的 Checkpoint 对象
            saved_checkpoint = Checkpoint(
                video_path="/fake/video.mp4",
                video_name="video.mp4",
                audio_path="/tmp/audio.wav",
                processed_segments=[],
                last_segment_index=0,
                stage="transcription"
            )
            mock_cm_instance.load_checkpoint.return_value = saved_checkpoint
            mock_cm_class.return_value = mock_cm_instance

            from processor import VideoProcessor

            vp = VideoProcessor()

            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
                video_path = f.name

            try:
                with patch.object(vp, '_extract_audio', return_value='/tmp/audio.wav'), \
                     patch.object(vp, '_cleanup'):
                    vp.process_video(video_path, progress_tracker=None)

                # 验证 has_checkpoint 被调用
                assert mock_cm_instance.has_checkpoint.called, \
                    "has_checkpoint should be called to check for existing checkpoint"
            finally:
                if os.path.exists(video_path):
                    os.remove(video_path)

    def test_process_video_resumes_from_checkpoint(self):
        """测试处理视频从断点恢复"""
        from checkpoint_manager import Checkpoint

        with patch('processor.WhisperEngine') as mock_engine_class, \
             patch('processor.SRTSplitter') as mock_splitter_class, \
             patch('processor.CheckpointManager') as mock_cm_class:

            mock_engine = MagicMock()
            mock_engine.transcribe_with_timestamps.return_value = []
            mock_engine_class.return_value = mock_engine

            mock_splitter = MagicMock()
            mock_splitter.split_if_needed.return_value = ["/tmp/test.srt"]
            mock_splitter_class.return_value = mock_splitter

            mock_cm_instance = MagicMock()
            # 模拟有断点存在，且包含已处理的片段
            mock_cm_instance.has_checkpoint.return_value = True
            saved_checkpoint = Checkpoint(
                video_path="/fake/video.mp4",
                video_name="video.mp4",
                audio_path="/tmp/audio.wav",
                processed_segments=[{"start": 0.0, "end": 2.5, "text": "已处理"}],
                last_segment_index=5,
                stage="transcription"
            )
            mock_cm_instance.load_checkpoint.return_value = saved_checkpoint
            mock_cm_class.return_value = mock_cm_instance

            from processor import VideoProcessor

            vp = VideoProcessor()

            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
                video_path = f.name

            try:
                with patch.object(vp, '_extract_audio', return_value='/tmp/audio.wav'), \
                     patch.object(vp, '_cleanup'):
                    vp.process_video(video_path, progress_tracker=None)

                # 验证 load_checkpoint 被调用来恢复进度
                assert mock_cm_instance.load_checkpoint.called, \
                    "load_checkpoint should be called to resume from checkpoint"
            finally:
                if os.path.exists(video_path):
                    os.remove(video_path)

    def test_process_video_deletes_checkpoint_on_success(self):
        """测试处理成功后删除断点"""
        with patch('processor.WhisperEngine') as mock_engine_class, \
             patch('processor.SRTSplitter') as mock_splitter_class, \
             patch('processor.CheckpointManager') as mock_cm_class:

            mock_engine = MagicMock()
            mock_engine.transcribe_with_timestamps.return_value = []
            mock_engine_class.return_value = mock_engine

            mock_splitter = MagicMock()
            mock_splitter.split_if_needed.return_value = ["/tmp/test.srt"]
            mock_splitter_class.return_value = mock_splitter

            mock_cm_instance = MagicMock()
            mock_cm_instance.has_checkpoint.return_value = False
            mock_cm_class.return_value = mock_cm_instance

            from processor import VideoProcessor

            vp = VideoProcessor()

            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
                video_path = f.name

            try:
                with patch.object(vp, '_extract_audio', return_value='/tmp/audio.wav'), \
                     patch.object(vp, '_cleanup'):
                    vp.process_video(video_path, progress_tracker=None)

                # 验证 delete_checkpoint 在成功后被调用
                assert mock_cm_instance.delete_checkpoint.called, \
                    "delete_checkpoint should be called after successful processing"
            finally:
                if os.path.exists(video_path):
                    os.remove(video_path)
