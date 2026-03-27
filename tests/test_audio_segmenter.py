"""
测试 audio_segmenter.py 音频分段模块
TDD RED 阶段：编写会失败的测试
"""
import os
import pytest
import tempfile
import shutil
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path


class TestAudioSegmenterInit:
    """测试 AudioSegmenter 初始化"""

    def test_init_default_segment_duration(self):
        """测试默认分段时长是 600 秒"""
        from audio_segmenter import AudioSegmenter

        segmenter = AudioSegmenter()
        assert segmenter.segment_duration == 600

    def test_init_custom_segment_duration(self):
        """测试自定义分段时长"""
        from audio_segmenter import AudioSegmenter

        segmenter = AudioSegmenter(segment_duration=300)
        assert segmenter.segment_duration == 300

    def test_segment_duration_type_is_int(self):
        """测试分段时长是整数类型"""
        from audio_segmenter import AudioSegmenter

        segmenter = AudioSegmenter(segment_duration=120)
        assert isinstance(segmenter.segment_duration, int)


class TestAudioSegmenterSplitByDuration:
    """测试 split_by_duration 方法"""

    def setup_method(self):
        """每个测试方法前创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """每个测试方法后清理临时目录"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch('audio_segmenter.ffmpeg')
    def test_split_600_seconds_into_2_segments(self, mock_ffmpeg):
        """测试 600 秒音频分成 2 段（每段 300 秒）"""
        from audio_segmenter import AudioSegmenter

        # 模拟 ffmpeg 获取音频时长
        mock_stream = MagicMock()
        mock_ffmpeg.input.return_value = mock_stream
        mock_ffmpeg.output.return_value = mock_stream
        mock_stream.__truediv__ = MagicMock(return_value=mock_stream)
        mock_ffmpeg.run = MagicMock()

        # 模拟 ffmpeg.probe 返回音频时长 600 秒
        mock_ffmpeg.probe.return_value = {'format': {'duration': '600.0'}}

        # 创建模拟的音频文件
        audio_path = os.path.join(self.temp_dir, "test_audio.wav")
        Path(audio_path).touch()

        segmenter = AudioSegmenter(segment_duration=300)
        result = segmenter.split_by_duration(audio_path)

        # 验证返回了 2 个分片文件
        assert len(result) == 2
        # 验证文件名格式
        assert "segment_0.wav" in result[0]
        assert "segment_1.wav" in result[1]

    @patch('audio_segmenter.ffmpeg')
    def test_split_exactly_600_seconds(self, mock_ffmpeg):
        """测试刚好 600 秒的音频（边界测试）"""
        from audio_segmenter import AudioSegmenter

        mock_stream = MagicMock()
        mock_ffmpeg.input.return_value = mock_stream
        mock_ffmpeg.output.return_value = mock_stream
        mock_stream.__truediv__ = MagicMock(return_value=mock_stream)
        mock_ffmpeg.run = MagicMock()

        audio_path = os.path.join(self.temp_dir, "test_audio.wav")
        Path(audio_path).touch()

        segmenter = AudioSegmenter(segment_duration=600)
        result = segmenter.split_by_duration(audio_path)

        # 刚好 600 秒应该只有 1 段
        assert len(result) == 1
        assert "segment_0.wav" in result[0]

    @patch('audio_segmenter.ffmpeg')
    def test_split_less_than_one_segment(self, mock_ffmpeg):
        """测试不足一段的音频（如 300 秒）"""
        from audio_segmenter import AudioSegmenter

        mock_stream = MagicMock()
        mock_ffmpeg.input.return_value = mock_stream
        mock_ffmpeg.output.return_value = mock_stream
        mock_stream.__truediv__ = MagicMock(return_value=mock_stream)
        mock_ffmpeg.run = MagicMock()

        audio_path = os.path.join(self.temp_dir, "test_audio.wav")
        Path(audio_path).touch()

        segmenter = AudioSegmenter(segment_duration=600)
        result = segmenter.split_by_duration(audio_path)

        # 不足一段应该只有 1 个分片
        assert len(result) == 1

    @patch('audio_segmenter.ffmpeg')
    def test_split_calls_ffmpeg_correctly(self, mock_ffmpeg):
        """验证 ffmpeg 调用参数正确"""
        from audio_segmenter import AudioSegmenter

        mock_stream = MagicMock()
        mock_ffmpeg.input.return_value = mock_stream
        mock_ffmpeg.output.return_value = mock_stream
        mock_stream.__truediv__ = MagicMock(return_value=mock_stream)
        mock_ffmpeg.run = MagicMock()

        audio_path = os.path.join(self.temp_dir, "test_audio.wav")
        Path(audio_path).touch()

        segmenter = AudioSegmenter(segment_duration=600)
        segmenter.split_by_duration(audio_path)

        # 验证 ffmpeg.input 被调用
        assert mock_ffmpeg.input.called
        # 验证 ffmpeg.output 被调用
        assert mock_ffmpeg.output.called

    @patch('audio_segmenter.ffmpeg')
    def test_split_segments_saved_to_temp_dir(self, mock_ffmpeg):
        """验证分片文件保存到 TEMP_DIR"""
        from audio_segmenter import AudioSegmenter
        from config import TEMP_DIR

        mock_stream = MagicMock()
        mock_ffmpeg.input.return_value = mock_stream
        mock_ffmpeg.output.return_value = mock_stream
        mock_stream.__truediv__ = MagicMock(return_value=mock_stream)
        mock_ffmpeg.run = MagicMock()

        audio_path = os.path.join(self.temp_dir, "test_audio.wav")
        Path(audio_path).touch()

        segmenter = AudioSegmenter(segment_duration=600)
        result = segmenter.split_by_duration(audio_path)

        # 验证分片路径在 TEMP_DIR 中
        for segment_path in result:
            assert segment_path.startswith(TEMP_DIR)


class TestAudioSegmenterMergeTranscripts:
    """测试 merge_transcripts 方法"""

    def test_merge_two_segments_timestamps(self):
        """测试合并两段转写结果，时间戳正确偏移"""
        from audio_segmenter import AudioSegmenter

        segmenter = AudioSegmenter(segment_duration=600)

        # 第一段：0-100秒
        segment1_results = [
            {"start": 0.0, "end": 10.0, "text": "第一段第一句"},
            {"start": 10.0, "end": 20.0, "text": "第一段第二句"},
        ]

        # 第二段：600-700秒（实际偏移后）
        segment2_results = [
            {"start": 0.0, "end": 10.0, "text": "第二段第一句"},
            {"start": 10.0, "end": 20.0, "text": "第二段第二句"},
        ]

        segment_results = [segment1_results, segment2_results]
        merged = segmenter.merge_transcripts(segment_results)

        # 验证总段数
        assert len(merged) == 4

        # 验证第一段时间戳未变
        assert merged[0]["start"] == 0.0
        assert merged[0]["end"] == 10.0
        assert merged[1]["start"] == 10.0
        assert merged[1]["end"] == 20.0

        # 验证第二段时间戳已偏移 600 秒
        assert merged[2]["start"] == 600.0
        assert merged[2]["end"] == 610.0
        assert merged[3]["start"] == 610.0
        assert merged[3]["end"] == 620.0

    def test_merge_three_segments_timestamps(self):
        """测试合并三段转写结果"""
        from audio_segmenter import AudioSegmenter

        segmenter = AudioSegmenter(segment_duration=600)

        segment1 = [{"start": 0.0, "end": 5.0, "text": "段1"}]
        segment2 = [{"start": 0.0, "end": 5.0, "text": "段2"}]
        segment3 = [{"start": 0.0, "end": 5.0, "text": "段3"}]

        segment_results = [segment1, segment2, segment3]
        merged = segmenter.merge_transcripts(segment_results)

        assert len(merged) == 3
        # 验证时间戳偏移
        assert merged[0]["start"] == 0.0
        assert merged[1]["start"] == 600.0
        assert merged[2]["start"] == 1200.0

    def test_merge_empty_list(self):
        """测试空列表处理"""
        from audio_segmenter import AudioSegmenter

        segmenter = AudioSegmenter(segment_duration=600)
        merged = segmenter.merge_transcripts([])

        assert merged == []

    def test_merge_single_segment(self):
        """测试单段转写结果（无偏移）"""
        from audio_segmenter import AudioSegmenter

        segmenter = AudioSegmenter(segment_duration=600)

        single_segment = [
            {"start": 10.0, "end": 20.0, "text": "只有一段"},
            {"start": 20.0, "end": 30.0, "text": "第二句"},
        ]

        merged = segmenter.merge_transcripts([single_segment])

        assert len(merged) == 2
        # 单段不应有时区偏移
        assert merged[0]["start"] == 10.0
        assert merged[1]["start"] == 20.0

    def test_merge_preserves_text_content(self):
        """验证合并后文本内容不变"""
        from audio_segmenter import AudioSegmenter

        segmenter = AudioSegmenter(segment_duration=600)

        segment1 = [{"start": 0.0, "end": 10.0, "text": "Hello"}]
        segment2 = [{"start": 0.0, "end": 10.0, "text": "World"}]

        merged = segmenter.merge_transcripts([segment1, segment2])

        assert merged[0]["text"] == "Hello"
        assert merged[1]["text"] == "World"

    def test_merge_with_custom_segment_duration(self):
        """测试自定义分段时长（300秒）"""
        from audio_segmenter import AudioSegmenter

        segmenter = AudioSegmenter(segment_duration=300)

        segment1 = [{"start": 0.0, "end": 5.0, "text": "第一段"}]
        segment2 = [{"start": 0.0, "end": 5.0, "text": "第二段"}]
        segment3 = [{"start": 0.0, "end": 5.0, "text": "第三段"}]

        merged = segmenter.merge_transcripts([segment1, segment2, segment3])

        # 验证 300 秒偏移
        assert merged[0]["start"] == 0.0
        assert merged[1]["start"] == 300.0
        assert merged[2]["start"] == 600.0


class TestAudioSegmenterEdgeCases:
    """测试边界情况"""

    def test_merge_with_empty_segment(self):
        """测试某段结果为空列表"""
        from audio_segmenter import AudioSegmenter

        segmenter = AudioSegmenter(segment_duration=600)

        segment1 = [{"start": 0.0, "end": 10.0, "text": "第一段"}]
        segment2 = []  # 空段
        segment3 = [{"start": 0.0, "end": 10.0, "text": "第三段"}]

        merged = segmenter.merge_transcripts([segment1, segment2, segment3])

        assert len(merged) == 2
        assert merged[0]["text"] == "第一段"
        assert merged[1]["text"] == "第三段"

    def test_merge_with_non_overlapping_timestamps(self):
        """测试合并具有连续时间戳的段落"""
        from audio_segmenter import AudioSegmenter

        segmenter = AudioSegmenter(segment_duration=600)

        # 第一段的时间戳已经是连续的非零开始
        segment1 = [{"start": 5.0, "end": 15.0, "text": "起始于5秒"}]
        segment2 = [{"start": 0.0, "end": 10.0, "text": "第二段起始"}]

        merged = segmenter.merge_transcripts([segment1, segment2])

        assert len(merged) == 2
        assert merged[0]["start"] == 5.0
        assert merged[1]["start"] == 600.0  # 偏移 600 秒


class TestAudioSegmenterIntegration:
    """集成测试（需要真实 ffmpeg，但不实际运行转写）"""

    def setup_method(self):
        """每个测试方法前创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """每个测试方法后清理临时目录"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch('audio_segmenter.ffmpeg')
    def test_full_workflow_split_and_merge(self, mock_ffmpeg):
        """测试完整的分段和合并工作流"""
        from audio_segmenter import AudioSegmenter

        mock_stream = MagicMock()
        mock_ffmpeg.input.return_value = mock_stream
        mock_ffmpeg.output.return_value = mock_stream
        mock_stream.__truediv__ = MagicMock(return_value=mock_stream)
        mock_ffmpeg.run = MagicMock()

        audio_path = os.path.join(self.temp_dir, "test_audio.wav")
        Path(audio_path).touch()

        segmenter = AudioSegmenter(segment_duration=600)

        # 1. 分段
        segments = segmenter.split_by_duration(audio_path)

        # 2. 模拟每段的转写结果
        segment_results = []
        for i, seg_path in enumerate(segments):
            # 每段生成 2 个转写结果
            segment_results.append([
                {"start": float(i * 10), "end": float(i * 10 + 5), "text": f"段{i}句1"},
                {"start": float(i * 10 + 5), "end": float(i * 10 + 10), "text": f"段{i}句2"},
            ])

        # 3. 合并转写结果
        merged = segmenter.merge_transcripts(segment_results)

        # 4. 验证
        expected_count = len(segments) * 2
        assert len(merged) == expected_count
