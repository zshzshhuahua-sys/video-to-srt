# Video to SRT - Docker 配置
# 注意: Docker 容器内无法使用 Mac CoreML 加速，Linux 服务器部署专用

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖 (ffmpeg)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建输出目录
RUN mkdir -p /app/output /app/temp_uploads

# 暴露端口
EXPOSE 8501

# 环境变量
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# 启动命令
CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0"]
