"""
SRT 字幕切分工具
当 SRT 文件过大时，按时间或大小切分
"""
import os
from config import SRT_SPLIT_SIZE


class SRTSplitter:
    """SRT 字幕文件切分器"""

    def __init__(self, split_size: int = SRT_SPLIT_SIZE):
        """
        初始化切分器

        Args:
            split_size: 切分阈值 (字节)，默认 10MB
        """
        self.split_size = split_size

    def split_if_needed(self, srt_path: str) -> list:
        """
        检查文件大小，必要时切分

        Args:
            srt_path: SRT 文件路径

        Returns:
            list: 切分后的文件路径列表
        """
        file_size = os.path.getsize(srt_path)

        if file_size < self.split_size:
            print(f"[SRT] 文件大小 {file_size / 1024 / 1024:.1f}MB < {self.split_size / 1024 / 1024:.1f}MB，无需切分")
            return [srt_path]

        print(f"[SRT] 文件大小 {file_size / 1024 / 1024:.1f}MB >= {self.split_size / 1024 / 1024:.1f}MB，开始切分")
        return self._split_by_time(srt_path)

    def _split_by_time(self, srt_path: str, segment_minutes: int = 30) -> list:
        """
        按时间切分 SRT 文件

        Args:
            srt_path: SRT 文件路径
            segment_minutes: 每段时长(分钟)

        Returns:
            list: 切分后的文件路径列表
        """
        # 读取原始 SRT
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()

        entries = self._parse_srt(content)
        if not entries:
            return [srt_path]

        # 计算切分点
        split_points = self._find_split_points(entries, segment_minutes * 60)

        if len(split_points) <= 1:
            return [srt_path]

        # 执行切分
        base_name = os.path.splitext(srt_path)[0]
        output_files = []

        for i, split_idx in enumerate(split_points):
            segment_entries = entries[split_idx:split_points[i + 1] if i + 1 < len(split_points) else None]
            output_path = f"{base_name}_part{i + 1}.srt"
            self._write_srt(output_path, segment_entries, start_index=split_idx + 1)
            output_files.append(output_path)
            print(f"[SRT] 已保存: {output_path}")

        # 删除原文件
        os.remove(srt_path)
        print(f"[SRT] 已删除原文件: {srt_path}")

        return output_files

    def _parse_srt(self, content: str) -> list:
        """
        解析 SRT 内容

        Returns:
            list: [{'index': int, 'start': str, 'end': str, 'text': str}, ...]
        """
        entries = []
        blocks = content.strip().split("\n\n")

        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) >= 3:
                try:
                    entry = {
                        "index": int(lines[0]),
                        "time_range": lines[1],
                        "text": "\n".join(lines[2:])
                    }
                    # 解析时间
                    times = lines[1].split(" --> ")
                    entry["start_seconds"] = self._time_to_seconds(times[0].strip())
                    entry["end_seconds"] = self._time_to_seconds(times[1].strip())
                    entries.append(entry)
                except (ValueError, IndexError):
                    continue

        return entries

    def _time_to_seconds(self, time_str: str) -> float:
        """将 SRT 时间格式转换为秒

        Args:
            time_str: SRT 时间格式字符串，如 "00:00:00,000"

        Returns:
            float: 秒数
        """
        # SRT 格式: 00:00:00,000 (小时:分钟:秒,毫秒)
        # 先把逗号替换成点，以便正确解析毫秒
        time_str = time_str.replace(",", ".")
        parts = time_str.split(":")

        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        elif len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)

        return 0.0

    def _find_split_points(self, entries: list, segment_seconds: int) -> list:
        """
        找到切分点索引

        基于累积时长切分：当 entry 的 start_seconds >= segment_seconds * (i+1) 时切分

        Args:
            entries: SRT 条目列表
            segment_seconds: 每段秒数

        Returns:
            list: 切分点索引列表
        """
        if not entries:
            return []

        split_points = [0]
        current_segment = 1  # 当前应该是第几段（从1开始）

        for i, entry in enumerate(entries):
            # 当 entry 的 start_seconds 达到当前段的时长阈值时，切分
            threshold = segment_seconds * current_segment
            if entry["start_seconds"] >= threshold:
                split_points.append(i)
                current_segment += 1

        return split_points

    def _write_srt(self, output_path: str, entries: list, start_index: int = 1):
        """写入 SRT 文件"""
        with open(output_path, "w", encoding="utf-8") as f:
            for i, entry in enumerate(entries):
                index = start_index + i
                f.write(f"{index}\n")
                f.write(f"{entry['time_range']}\n")
                f.write(f"{entry['text']}\n")
                f.write("\n")
