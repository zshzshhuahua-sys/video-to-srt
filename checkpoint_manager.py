"""
断点续传管理器
用于保存和恢复视频处理进度
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict
import os
import json
import time


@dataclass
class Checkpoint:
    """断点记录"""
    video_path: str
    video_name: str
    audio_path: str = ""  # 已提取的音频路径
    processed_segments: List[Dict] = field(default_factory=list)  # 已完成的片段
    last_segment_index: int = -1
    stage: str = "idle"  # ProcessingStage value
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'Checkpoint':
        return cls(**data)


class CheckpointManager:
    """断点续传管理器"""

    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True)

    def _get_checkpoint_path(self, video_name: str) -> str:
        """获取断点文件路径"""
        # 清理文件名中的非法字符
        safe_name = "".join(c for c in video_name if c.isalnum() or c in "._- ")
        return os.path.join(self.checkpoint_dir, f"{safe_name}.json")

    def save_checkpoint(self, checkpoint: Checkpoint):
        """保存断点"""
        checkpoint.updated_at = time.time()
        path = self._get_checkpoint_path(checkpoint.video_name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(checkpoint.to_dict(), f, ensure_ascii=False, indent=2)

    def load_checkpoint(self, video_name: str) -> Optional[Checkpoint]:
        """加载断点"""
        path = self._get_checkpoint_path(video_name)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return Checkpoint.from_dict(data)
        except (json.JSONDecodeError, TypeError):
            return None

    def has_checkpoint(self, video_name: str) -> bool:
        """检查是否有未完成的断点"""
        checkpoint = self.load_checkpoint(video_name)
        return checkpoint is not None and checkpoint.last_segment_index >= 0

    def delete_checkpoint(self, video_name: str):
        """删除断点"""
        path = self._get_checkpoint_path(video_name)
        if os.path.exists(path):
            os.remove(path)
