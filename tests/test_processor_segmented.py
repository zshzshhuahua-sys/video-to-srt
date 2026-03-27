"""
测试 processor.py 分段转写功能
"""
import os
import pytest
import tempfile
import shutil
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path


class TestProcessorSegmentedTranscription:
    """测试 VideoProcessor 的分段转写功能"""

    def setup_method(self):
        """每个测试方法前创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """每个测试方法后清理临时目录"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch('processor.AudioSegmenter')
    @patch('processor.WhisperEngine')
    @patch('processor.SRTSplitter')
    def test_processor_initializes_segmenter(self, mock_splitter, mock_whisper, mock_segmenter):
        """测试 VideoProcessor 初始化时创建 AudioSegmenter"""
        from processor import VideoProcessor
        from config import AUDIO_SEGMENT_DURATION

        processor = VideoProcessor()

        # 验证 AudioSegmenter 被创建，传入正确的分段时长
        mock_segmenter.assert_called_once_with(segment_duration=AUDIO_SEGMENT_DURATION)

    @patch('processor.AudioSegmenter')
    @patch('processor.WhisperEngine')
    @patch('processor.SRTSplitter')
    def test_transcribe_audio_splits_then_transcribes(self, mock_splitter, mock_whisper, mock_segmenter):
        """测试 _transcribe_audio 先分段再转写"""
        from processor import VideoProcessor

        # 创建 mock segmenter
        mock_seg_instance = MagicMock()
        mock_seg_instance.split_by_duration.return_value = ['/tmp/seg0.wav', '/tmp/seg1.wav']
        mock_seg_instance.merge_transcripts.return_value = [
            {'start': 0.0, 'end': 10.0, 'text': '第一段'},
            {'start': 600.0, 'end': 610.0, 'text': '第二段'},
        ]
        mock_segmenter.return_value = mock_seg_instance

        # 创建 mock whisper
        mock_whisper_instance = MagicMock()
        mock_whisper_instance.transcribe_with_timestamps.side_effect = [
            [{'start': 0.0, 'end': 10.0, 'text': '第一段'}],
            [{'start': 0.0, 'end': 10.0, 'text': '第二段'}],
        ]
        mock_whisper.return_value = mock_whisper_instance

        processor = VideoProcessor()
        processor.segmenter = mock_seg_instance
        processor.whisper = mock_whisper_instance

        result = processor._transcribe_audio('/tmp/audio.wav')

        # 验证先调用分段
        mock_seg_instance.split_by_duration.assert_called_once_with('/tmp/audio.wav')

        # 验证转写了2段
        assert mock_whisper_instance.transcribe_with_timestamps.call_count == 2

        # 验证返回合并后的结果
        assert len(result) == 2
        assert result[0]['text'] == '第一段'
        assert result[1]['text'] == '第二段'

    @patch('processor.AudioSegmenter')
    @patch('processor.WhisperEngine')
    @patch('processor.SRTSplitter')
    def test_transcribe_audio_resumes_from_checkpoint(self, mock_splitter, mock_whisper, mock_segmenter):
        """测试 _transcribe_audio 从断点恢复（跳过已完成的段）"""
        from processor import VideoProcessor
        from checkpoint_manager import Checkpoint

        # 创建 mock segmenter - 模拟3个分段
        mock_seg_instance = MagicMock()
        mock_seg_instance.split_by_duration.return_value = ['/tmp/seg0.wav', '/tmp/seg1.wav', '/tmp/seg2.wav']
        mock_seg_instance.merge_transcripts.return_value = [
            {'start': 0.0, 'end': 10.0, 'text': '第一段'},
        ]
        mock_segmenter.return_value = mock_seg_instance

        # 创建 mock whisper - 2次调用（跳过第一段，处理第二、三段）
        mock_whisper_instance = MagicMock()
        mock_whisper_instance.transcribe_with_timestamps.side_effect = [
            [{'start': 0.0, 'end': 10.0, 'text': '第二段'}],
            [{'start': 0.0, 'end': 10.0, 'text': '第三段'}],
        ]
        mock_whisper.return_value = mock_whisper_instance

        # 创建 checkpoint（last_segment_index=0 表示第一段已完成，所以从index=1开始）
        checkpoint = Checkpoint(
            video_path='/tmp/video.mp4',
            video_name='video.mp4',
            audio_path='/tmp/audio.wav',
            processed_segments=[{'start': 0.0, 'end': 10.0, 'text': '第一段'}],
            last_segment_index=0,
            stage='transcription_in_progress'
        )

        processor = VideoProcessor()
        processor.segmenter = mock_seg_instance
        processor.whisper = mock_whisper_instance
        processor.checkpoint_manager = MagicMock()

        result = processor._transcribe_audio('/tmp/audio.wav', checkpoint=checkpoint)

        # 验证 whisper 被调用2次（跳过第一段，从第二段index=1开始处理）
        assert mock_whisper_instance.transcribe_with_timestamps.call_count == 2

    @patch('processor.AudioSegmenter')
    @patch('processor.WhisperEngine')
    @patch('processor.SRTSplitter')
    def test_transcribe_audio_saves_checkpoint_after_each_segment(self, mock_splitter, mock_whisper, mock_segmenter):
        """测试每段转写完成后都保存断点"""
        from processor import VideoProcessor

        mock_seg_instance = MagicMock()
        mock_seg_instance.split_by_duration.return_value = ['/tmp/seg0.wav', '/tmp/seg1.wav']
        # 每次 checkpoint 保存时调用 merge
        mock_seg_instance.merge_transcripts.return_value = [{'start': 0.0, 'end': 10.0, 'text': 'text'}]
        mock_segmenter.return_value = mock_seg_instance

        mock_whisper_instance = MagicMock()
        mock_whisper_instance.transcribe_with_timestamps.side_effect = [
            [{'start': 0.0, 'end': 10.0, 'text': '第一段'}],
            [{'start': 0.0, 'end': 10.0, 'text': '第二段'}],
        ]
        mock_whisper.return_value = mock_whisper_instance

        mock_checkpoint_manager = MagicMock()
        processor = VideoProcessor()
        processor.segmenter = mock_seg_instance
        processor.whisper = mock_whisper_instance
        processor.checkpoint_manager = mock_checkpoint_manager

        processor._transcribe_audio('/tmp/audio.wav')

        # 验证保存了2次断点（每段一次）
        assert mock_checkpoint_manager.save_checkpoint.call_count == 2


class TestTimestampOffset:
    """测试时间戳偏移正确性"""

    def test_merge_transcripts_offsets_second_segment(self):
        """验证第二段的时间戳正确偏移 600 秒"""
        from audio_segmenter import AudioSegmenter

        segmenter = AudioSegmenter(segment_duration=600)

        segment1 = [{'start': 10.0, 'end': 20.0, 'text': '第一段内容'}]
        segment2 = [{'start': 5.0, 'end': 15.0, 'text': '第二段内容'}]

        result = segmenter.merge_transcripts([segment1, segment2])

        assert result[0]['start'] == 10.0  # 第一段不偏移
        assert result[0]['end'] == 20.0

        assert result[1]['start'] == 605.0  # 第二段偏移 600 秒
        assert result[1]['end'] == 615.0
        assert result[1]['text'] == '第二段内容'

    def test_merge_transcripts_handles_three_segments(self):
        """验证三段转写的时间戳偏移"""
        from audio_segmenter import AudioSegmenter

        segmenter = AudioSegmenter(segment_duration=600)

        segments = [
            [{'start': 0.0, 'end': 10.0, 'text': '第1段'}],
            [{'start': 0.0, 'end': 10.0, 'text': '第2段'}],
            [{'start': 0.0, 'end': 10.0, 'text': '第3段'}],
        ]

        result = segmenter.merge_transcripts(segments)

        assert result[0]['start'] == 0.0
        assert result[1]['start'] == 600.0  # 第2段偏移600
        assert result[2]['start'] == 1200.0  # 第3段偏移1200

    def test_merge_transcripts_single_segment_no_offset(self):
        """验证单段转写没有偏移"""
        from audio_segmenter import AudioSegmenter

        segmenter = AudioSegmenter(segment_duration=600)

        segments = [[{'start': 100.0, 'end': 110.0, 'text': '只有一段'}]]

        result = segmenter.merge_transcripts(segments)

        assert result[0]['start'] == 100.0  # 不偏移
        assert result[0]['end'] == 110.0
