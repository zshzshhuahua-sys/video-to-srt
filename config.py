"""
配置项
支持从环境变量覆盖
"""
import os

# Whisper 模型 - small 推荐，M4 16GB 够用
# 支持环境变量覆盖: WHISPER_MODEL
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small")

# 支持的模型列表
WHISPER_MODELS = ["tiny", "base", "small", "medium"]

# 最大文件大小 (10GB) - 支持环境变量覆盖: MAX_FILE_SIZE
MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", str(10 * 1024**3)))

# 音频采样率 - 支持环境变量覆盖: AUDIO_SAMPLE_RATE
AUDIO_SAMPLE_RATE = int(os.environ.get("AUDIO_SAMPLE_RATE", "16000"))

# 视频分段时长 (秒) - 30分钟 - 支持环境变量覆盖: SEGMENT_DURATION
SEGMENT_DURATION = int(os.environ.get("SEGMENT_DURATION", str(30 * 60)))

# SRT 切分阈值 (10MB) - 支持环境变量覆盖: SRT_SPLIT_SIZE
SRT_SPLIT_SIZE = int(os.environ.get("SRT_SPLIT_SIZE", str(10 * 1024**2)))

# 支持的视频格式 - 支持环境变量覆盖: SUPPORTED_FORMATS (逗号分隔)
_SUPPORTED_FORMATS_STR = os.environ.get("SUPPORTED_FORMATS", "mp4,avi,mkv,mov,webm")
SUPPORTED_FORMATS = [fmt.strip() for fmt in _SUPPORTED_FORMATS_STR.split(",")]

# 临时文件目录
TEMP_DIR = os.environ.get("TEMP_DIR", os.path.join(os.path.dirname(__file__), "temp"))

# 默认输出目录
DEFAULT_OUTPUT = os.environ.get("DEFAULT_OUTPUT", os.path.join(os.path.dirname(__file__), "output"))

# 日志配置
LOG_FORMAT = "%Y-%m-%d %H:%M:%S"
