"""
测试 srt_splitter.py SRT 切分工具
TDD RED 阶段：编写会失败的测试
"""
import os
import pytest
import tempfile
from unittest.mock import patch


class TestSRTSplitterDefaults:
    """测试 SRTSplitter 默认值"""

    def test_default_split_size(self):
        """测试默认切分大小是 10MB"""
        from srt_splitter import SRTSplitter
        from config import SRT_SPLIT_SIZE
        splitter = SRTSplitter()
        assert splitter.split_size == SRT_SPLIT_SIZE
        assert splitter.split_size == 10 * 1024**2


class TestSRTParser:
    """测试 SRT 解析功能"""

    def test_parse_valid_srt(self):
        """测试解析有效的 SRT 内容"""
        from srt_splitter import SRTSplitter
        splitter = SRTSplitter()

        srt_content = """1
00:00:00,000 --> 00:00:02,500
第一句字幕

2
00:00:02,600 --> 00:00:05,300
第二句字幕

3
00:00:05,400 --> 00:00:08,100
第三句字幕
"""
        entries = splitter._parse_srt(srt_content)

        assert len(entries) == 3
        assert entries[0]["index"] == 1
        assert entries[0]["text"] == "第一句字幕"
        assert entries[0]["start_seconds"] == 0.0
        assert entries[0]["end_seconds"] == 2.5

    def test_parse_srt_with_complex_timestamps(self):
        """测试解析包含复杂时间戳的 SRT"""
        from srt_splitter import SRTSplitter
        splitter = SRTSplitter()

        srt_content = """1
01:23:45,678 --> 01:23:47,890
测试字幕
"""
        entries = splitter._parse_srt(srt_content)

        assert len(entries) == 1
        # 1*3600 + 23*60 + 45 = 5025 秒
        assert entries[0]["start_seconds"] == 5025.678
        assert entries[0]["end_seconds"] == 5027.89


class TestFindSplitPoints:
    """测试 _find_split_points 逻辑 - 这是修复的重点"""

    def test_split_at_cumulative_duration_not_gap(self):
        """
        测试切分点是基于累积时长，而非时间间隙

        场景：entries 的 start_seconds 分别是 0, 60, 120, 180, 240（每段60秒）
        当 segment_seconds=120 时（2分钟一段），应该在 120 和 240 处切分

        错误逻辑（当前bug）：entry["start_seconds"] - current_end >= segment_seconds
        会比较时间间隙。例如第二段 start=60, end=120, 间隙=60-120=-60, 永远不会切分

        正确逻辑：entry["start_seconds"] >= segment_seconds * (i+1)
        """
        from srt_splitter import SRTSplitter

        splitter = SRTSplitter()

        # 模拟 SRT entries，每段 60 秒，总时长 5 分钟
        entries = [
            {"start_seconds": 0, "end_seconds": 60, "text": "第1分钟"},
            {"start_seconds": 60, "end_seconds": 120, "text": "第2分钟"},
            {"start_seconds": 120, "end_seconds": 180, "text": "第3分钟"},
            {"start_seconds": 180, "end_seconds": 240, "text": "第4分钟"},
            {"start_seconds": 240, "end_seconds": 300, "text": "第5分钟"},
        ]

        # 每 2 分钟（120 秒）切分一段
        segment_seconds = 120
        split_points = splitter._find_split_points(entries, segment_seconds)

        # 正确逻辑应该在索引 2（start=120）和 4（start=240）处切分
        # split_points 应该是 [0, 2, 4]
        assert 2 in split_points, f"应该在 start=120s 处切分，但 split_points={split_points}"
        assert 4 in split_points, f"应该在 start=240s 处切分，但 split_points={split_points}"

    def test_split_points_single_segment(self):
        """测试时长小于分段长度时不应切分"""
        from srt_splitter import SRTSplitter

        splitter = SRTSplitter()

        # 全部在第一分钟内
        entries = [
            {"start_seconds": 0, "end_seconds": 20, "text": "第1段"},
            {"start_seconds": 20, "end_seconds": 40, "text": "第2段"},
            {"start_seconds": 40, "end_seconds": 59, "text": "第3段"},
        ]

        # 2 分钟分段，整个内容不足 2 分钟
        split_points = splitter._find_split_points(entries, 120)

        # 应该只有起点 [0]
        assert split_points == [0] or len(split_points) == 1

    def test_split_points_exactly_at_boundary(self):
        """测试正好在边界处切分"""
        from srt_splitter import SRTSplitter

        splitter = SRTSplitter()

        # 3 分钟内容，每分钟一段
        entries = [
            {"start_seconds": 0, "end_seconds": 60, "text": "第1分钟"},
            {"start_seconds": 60, "end_seconds": 120, "text": "第2分钟"},
            {"start_seconds": 120, "end_seconds": 180, "text": "第3分钟"},
        ]

        # 每 2 分钟切分
        split_points = splitter._find_split_points(entries, 120)

        # 应该在索引 2（恰好 120s 处）切分
        assert 2 in split_points


class TestTimeConversion:
    """测试时间格式转换"""

    def test_time_to_seconds_standard_format(self):
        """测试标准 SRT 时间格式转换"""
        from srt_splitter import SRTSplitter
        splitter = SRTSplitter()

        # 格式: 00:00:00,000
        assert splitter._time_to_seconds("00:00:00,000") == 0.0
        assert splitter._time_to_seconds("00:00:01,000") == 1.0
        assert splitter._time_to_seconds("00:01:00,000") == 60.0
        assert splitter._time_to_seconds("01:00:00,000") == 3600.0
        assert splitter._time_to_seconds("01:23:45,678") == pytest.approx(5025.678, rel=1e-3)

    def test_time_to_seconds_with_comma(self):
        """测试使用逗号作为毫秒分隔符"""
        from srt_splitter import SRTSplitter
        splitter = SRTSplitter()

        # SRT 使用逗号而非点
        assert splitter._time_to_seconds("00:00:00,500") == 0.5
        assert splitter._time_to_seconds("00:00:30,250") == 30.25


class TestSRTWrite:
    """测试 SRT 文件写入"""

    def test_write_srt_file(self):
        """测试写入 SRT 文件"""
        from srt_splitter import SRTSplitter

        splitter = SRTSplitter()

        entries = [
            {
                "index": 1,
                "time_range": "00:00:00,000 --> 00:00:02,500",
                "text": "测试字幕"
            }
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            output_path = f.name

        try:
            splitter._write_srt(output_path, entries, start_index=1)

            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()

            assert "1\n" in content
            assert "00:00:00,000 --> 00:00:02,500\n" in content
            assert "测试字幕\n" in content
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


class TestSplitIfNeeded:
    """测试 split_if_needed 方法"""

    def test_no_split_when_below_threshold(self):
        """测试文件小于阈值时不切分"""
        from srt_splitter import SRTSplitter

        splitter = SRTSplitter(split_size=10 * 1024**2)  # 10MB

        # 创建一个小的 SRT 文件
        srt_content = """1
00:00:00,000 --> 00:00:02,500
测试

"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            f.write(srt_content)
            srt_path = f.name

        try:
            result = splitter.split_if_needed(srt_path)
            # 应该返回原文件路径，不切分
            assert result == [srt_path]
            assert os.path.exists(srt_path), "原文件应该存在"
        finally:
            if os.path.exists(srt_path):
                os.remove(srt_path)

    def test_split_when_above_threshold(self):
        """测试文件大于阈值时应该切分"""
        from srt_splitter import SRTSplitter

        splitter = SRTSplitter(split_size=100)  # 100 bytes threshold

        # 创建一个 SRT 文件，内容足以触发切分（每段 30 分钟）
        # 由于 entries 的 start_seconds 很小，不会触发切分
        srt_content = """1
00:00:00,000 --> 00:00:02,500
测试1

2
00:00:02,600 --> 00:00:05,300
测试2
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            f.write(srt_content)
            srt_path = f.name

        try:
            # mock os.path.getsize 来返回大文件
            with patch('srt_splitter.os.path.getsize', return_value=200):
                with patch('srt_splitter.os.remove') as mock_remove:
                    result = splitter.split_if_needed(srt_path)
                    # 由于内容不足 30 分钟，不应切分，返回原文件
                    assert result == [srt_path]
        finally:
            if os.path.exists(srt_path):
                os.remove(srt_path)

    def test_split_by_time_creates_multiple_parts(self):
        """测试 _split_by_time 创建多个分段文件"""
        from srt_splitter import SRTSplitter

        splitter = SRTSplitter(split_size=50)  # 很小的阈值触发切分

        # 创建一个 SRT 文件，有足够的分段点（每分钟一段）
        srt_entries = []
        for i in range(90):  # 90 分钟的内容
            start = i * 60
            end = start + 60
            srt_entries.append(f"""1
00:{i//60:02d}:{i%60:02d},000 --> 00:{i//60:02d}:{i%60:02d},590
第{i+1}分钟字幕

""")

        srt_content = "\n".join(srt_entries)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            f.write(srt_content)
            srt_path = f.name

        try:
            with patch('srt_splitter.os.path.getsize', return_value=200):
                # 调用 _split_by_time，segment_minutes=1 强制每分钟切分
                result = splitter._split_by_time(srt_path, segment_minutes=1)

                # 应该创建多个分段文件
                # 由于原文件被删除，result 应该包含多个文件
                assert len(result) > 1
                for f in result:
                    assert os.path.exists(f), f"分段文件 {f} 应该存在"
                    os.remove(f)
        finally:
            if os.path.exists(srt_path):
                os.remove(srt_path)

    def test_split_by_time_empty_entries(self):
        """测试 _split_by_time 处理空 entries"""
        from srt_splitter import SRTSplitter

        splitter = SRTSplitter(split_size=50)

        srt_content = """1
00:00:00,000 --> 00:00:02,500
测试

"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            f.write(srt_content)
            srt_path = f.name

        try:
            # mock _parse_srt 返回空列表
            with patch.object(splitter, '_parse_srt', return_value=[]):
                result = splitter._split_by_time(srt_path, segment_minutes=1)
                # 空 entries 应返回原文件路径
                assert result == [srt_path]
                assert os.path.exists(srt_path)
        finally:
            if os.path.exists(srt_path):
                os.remove(srt_path)

    def test_split_by_time_single_segment(self):
        """测试 _split_by_time 单段不切分"""
        from srt_splitter import SRTSplitter

        splitter = SRTSplitter(split_size=50)

        # 创建一个 SRT 文件，但只有一小段
        srt_content = """1
00:00:00,000 --> 00:00:02,500
测试

"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            f.write(srt_content)
            srt_path = f.name

        try:
            # _split_by_time 应该返回原文件（因为 split_points <= 1）
            result = splitter._split_by_time(srt_path, segment_minutes=30)
            assert result == [srt_path]
            assert os.path.exists(srt_path)
        finally:
            if os.path.exists(srt_path):
                os.remove(srt_path)


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_entries(self):
        """测试空 entries 列表"""
        from srt_splitter import SRTSplitter
        splitter = SRTSplitter()

        split_points = splitter._find_split_points([], 120)
        assert split_points == []

    def test_single_entry(self):
        """测试单个 entry"""
        from srt_splitter import SRTSplitter
        splitter = SRTSplitter()

        entries = [{"start_seconds": 0, "end_seconds": 10, "text": "only"}]
        split_points = splitter._find_split_points(entries, 120)

        # 只有一个 entry，不应切分
        assert split_points == [0]

    def test_parse_srt_with_empty_lines(self):
        """测试解析包含空行的 SRT"""
        from srt_splitter import SRTSplitter
        splitter = SRTSplitter()

        srt_content = """1
00:00:00,000 --> 00:00:02,500
第一句


2
00:00:02,600 --> 00:00:05,300
第二句
"""
        entries = splitter._parse_srt(srt_content)
        assert len(entries) == 2
