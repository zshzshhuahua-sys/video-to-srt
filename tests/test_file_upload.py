"""
测试 app.py 文件上传验证功能
TDD RED 阶段：编写会失败的测试
"""
import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock
import io


class MockUploadedFile:
    """模拟 Streamlit UploadedFile"""
    def __init__(self, name: str, size: int, content: bytes = None):
        self.name = name
        self.size = size  # Streamlit UploadedFile uses 'size' attribute
        self._content = content or (b"x" * size if size > 0 else b"")

    def read(self, size=-1):
        if size == -1:
            return self._content
        return self._content[:size]


class TestFileUploadValidation:
    """测试文件上传验证"""

    def test_reject_zero_byte_file(self):
        """测试拒绝 0 字节文件"""
        from app import validate_uploaded_file
        from config import MAX_FILE_SIZE

        # 创建 0 字节文件
        zero_file = MockUploadedFile("test.mp4", 0)

        # 应该抛出 ValueError
        with pytest.raises(ValueError, match="文件为空"):
            validate_uploaded_file(zero_file)

    def test_reject_oversized_file(self):
        """测试拒绝超过最大限制的文件"""
        from app import validate_uploaded_file
        from config import MAX_FILE_SIZE

        # 创建超过限制的文件 (MAX_FILE_SIZE + 1 字节)
        large_file = MockUploadedFile("test.mp4", MAX_FILE_SIZE + 1)

        with pytest.raises(ValueError, match="超过最大"):
            validate_uploaded_file(large_file)

    def test_reject_negative_size_file(self):
        """测试拒绝负数大小的文件"""
        from app import validate_uploaded_file

        # 创建负数大小的文件
        invalid_file = MockUploadedFile("test.mp4", -1)

        with pytest.raises(ValueError, match="无效"):
            validate_uploaded_file(invalid_file)

    def test_accept_valid_file(self):
        """测试接受有效大小的文件"""
        from app import validate_uploaded_file
        from config import MAX_FILE_SIZE

        # 创建有效大小的文件
        valid_file = MockUploadedFile("test.mp4", 1024 * 1024)  # 1MB

        # 不应抛出异常，返回文件大小
        result = validate_uploaded_file(valid_file)
        assert result == 1024 * 1024

    def test_accept_exactly_max_size_file(self):
        """测试接受恰好等于最大限制的文件"""
        from app import validate_uploaded_file
        from config import MAX_FILE_SIZE

        # 创建恰好等于最大限制的文件
        max_file = MockUploadedFile("test.mp4", MAX_FILE_SIZE)

        result = validate_uploaded_file(max_file)
        assert result == MAX_FILE_SIZE

    def test_validate_file_size_returns_size(self):
        """测试 validate_uploaded_file 返回文件大小"""
        from app import validate_uploaded_file

        file = MockUploadedFile("test.mp4", 5000)
        result = validate_uploaded_file(file)
        assert result == 5000


class TestFileUploadWithPathTraversal:
    """测试路径遍历防护"""

    def test_reject_path_traversal_in_filename(self):
        """测试拒绝路径遍历文件名"""
        from app import validate_uploaded_file

        # 尝试路径遍历
        malicious_file = MockUploadedFile("../../../etc/passwd", 100)

        with pytest.raises(ValueError, match="非法字符"):
            validate_uploaded_file(malicious_file)

    def test_accept_simple_filename(self):
        """测试接受简单文件名"""
        from app import validate_uploaded_file

        file = MockUploadedFile("video.mp4", 1000)
        result = validate_uploaded_file(file)
        assert result == 1000

    def test_accept_filename_with_spaces(self):
        """测试接受带空格的文件名"""
        from app import validate_uploaded_file

        file = MockUploadedFile("my video file.mp4", 1000)
        result = validate_uploaded_file(file)
        assert result == 1000

    def test_accept_chinese_filename(self):
        """测试接受中文文件名"""
        from app import validate_uploaded_file

        file = MockUploadedFile("许大直播：杠杆工具构造凸性策略.mp4", 1000)
        result = validate_uploaded_file(file)
        assert result == 1000
