# 视频转 SRT 字幕工具

将长视频(3-4小时)批量转换为 SRT 中文字幕，方便大模型分析。

## 环境要求

- macOS (Apple Silicon M4 推荐) 或 Linux 服务器
- Python 3.11+ (本地运行)
- Docker (容器运行)

## 两种运行方式

### 方式一: Docker 一键启动 (推荐)

```bash
# 1. 双击 start-docker.command 或手动运行
./start-docker.command

# 或使用 docker-compose
docker-compose up -d
```

然后访问 http://localhost:8501

**注意**: Docker 容器内无法使用 Mac CoreML 加速，如需最快速度请用本地方式。

---

### 方式二: 本地运行 (M4 Mac 加速)

```bash
# 1. 安装 FFmpeg
brew install ffmpeg

# 2. 安装 Python 依赖
pip install -r requirements.txt

# 3. 启动应用
./启动.command
# 或手动: streamlit run app.py
```

然后：
1. 在侧边栏选择 Whisper 模型 (默认 small)
2. 设置输出目录
3. 上传视频文件
4. 点击"开始转换"

## Whisper 模型选择

| 模型 | 推荐场景 |
|------|----------|
| tiny | 快速测试 |
| base | 低配设备 |
| **small** | **推荐，M4 16GB 够用** |
| medium | 高精度需求 |

## SRT 切分

当 SRT 文件超过阈值(默认 10MB)时会自动切分为多个文件。

## 技术栈

- [Streamlit](https://streamlit.io/) - 界面
- [Whisper](https://github.com/openai/whisper) - 语音识别
- [FFmpeg](https://ffmpeg.org/) - 音视频处理
