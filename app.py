"""
视频转 SRT 字幕工具 - Streamlit 主应用
"""
import streamlit as st
import os
import time
from datetime import datetime
from typing import Optional

from processor import VideoProcessor
from config import WHISPER_MODELS, DEFAULT_OUTPUT, MAX_FILE_SIZE, SUPPORTED_FORMATS
from exceptions import VideoProcessingError
from checkpoint_manager import CheckpointManager


def validate_uploaded_file(uploaded_file) -> int:
    """
    验证上传的文件

    Args:
        uploaded_file: Streamlit UploadedFile 对象

    Returns:
        int: 文件大小（字节）

    Raises:
        ValueError: 文件无效时（空文件、超大、非法文件名）
    """
    # 获取文件大小
    size = uploaded_file.size

    # 检查文件大小是否为负数或无效
    if size is None or size < 0:
        raise ValueError("无效的文件大小")

    # 检查是否为空文件
    if size == 0:
        raise ValueError("文件为空，请重新上传")

    # 检查是否超过最大限制
    if size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        raise ValueError(f"文件超过最大限制 ({max_mb:.0f}MB)")

    # 检查文件名是否包含路径遍历字符
    filename = uploaded_file.name
    if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
        raise ValueError("文件名包含非法字符")

    return size


def _format_eta(seconds: Optional[float]) -> str:
    """
    格式化 ETA 显示

    Args:
        seconds: 剩余秒数，None 表示无法计算

    Returns:
        str: 格式化的时间字符串 (如 "1:30" 或 "--:--" 如果无法计算)
    """
    if seconds is None:
        return "--:--"

    if seconds < 0:
        seconds = 0

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def _render_progress(task_data, eta: Optional[float] = None):
    """
    渲染进度条和阶段详情

    Args:
        task_data: ProcessingTask 对象
        eta: 预计剩余时间（秒）
    """
    percent = task_data.overall_progress_percent / 100.0
    st.progress(percent)

    # 显示 ETA
    eta_str = _format_eta(eta)
    st.caption(f"预计剩余时间: {eta_str}")

    # 显示阶段详情
    if task_data.stages:
        with st.expander("阶段详情", expanded=False):
            for name, stage in task_data.stages.items():
                status_icon = {
                    "idle": "⏳",
                    "processing": "🔄",
                    "completed": "✅",
                    "failed": "❌",
                    "cancelled": "⚠️"
                }.get(stage.status.value, "❓")

                st.text(f"{status_icon} {name}: {stage.percent}% - {stage.message}")


def _render_error(error: Exception):
    """
    渲染错误面板

    Args:
        error: 异常对象
    """
    if isinstance(error, VideoProcessingError):
        # 使用错误详情显示
        detail = error.to_detail()
        st.error(f"❌ {detail.message}")

        # 显示建议（如果有）
        if detail.suggestion:
            st.info(f"💡 建议: {detail.suggestion}")
    else:
        # 普通异常
        st.error(f"❌ {str(error)}")

# 页面配置
st.set_page_config(
    page_title="视频转 SRT 字幕工具",
    page_icon="🎬",
    layout="wide"
)

# 标题
st.title("🎬 视频转 SRT 字幕工具")
st.markdown("将长视频转换为 SRT 中文字幕，方便大模型分析")

# 初始化 session state
if "processing" not in st.session_state:
    st.session_state.processing = False
if "results" not in st.session_state:
    st.session_state.results = []
if "logs" not in st.session_state:
    st.session_state.logs = []


def log(message: str):
    """添加日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.logs.append(f"[{timestamp}] {message}")


def progress_callback(percent: int, message: str):
    """进度回调"""
    log(message)
    return percent


# 侧边栏设置
with st.sidebar:
    st.header("⚙️ 设置")

    # 模型选择
    model = st.radio(
        "选择 Whisper 模型",
        options=WHISPER_MODELS,
        index=2,  # small 默认
        help="small 推荐：精度和速度平衡，M4 16GB 够用"
    )

    st.caption("""
    | 模型 | 速度 | 精度 |
    |------|------|------|
    | tiny | 最快 | 较低 |
    | base | 快 | 一般 |
    | **small** | 中速 | **良好** |
    | medium | 慢 | 最好 |
    """)

    # 输出路径
    output_dir = st.text_input(
        "输出目录",
        value=DEFAULT_OUTPUT,
        help="SRT 文件保存位置"
    )

    # 自定义输出文件名
    custom_filename = st.text_input(
        "自定义文件名 (可选)",
        value="",
        placeholder="留空则使用原视频文件名",
        help="不填则自动使用原视频文件名"
    )

    # SRT 切分阈值
    split_mb = st.slider(
        "SRT 切分阈值 (MB)",
        min_value=5,
        max_value=50,
        value=10,
        step=5,
        help="当 SRT 文件超过此大小时会自动切分"
    )
    split_size = split_mb * 1024 * 1024

    st.divider()

    # 当前状态
    st.subheader("📊 状态")
    if st.session_state.processing:
        st.info("🔄 处理中...")
    else:
        st.success("✅ 就绪")


# 主区域
col1, col2 = st.columns([2, 1])

with col1:
    # 文件上传
    st.subheader("📤 上传视频文件")

    uploaded_files = st.file_uploader(
        "拖拽或选择视频文件",
        type=SUPPORTED_FORMATS,
        accept_multiple_files=True,
        help=f"支持格式: {', '.join(SUPPORTED_FORMATS)}"
    )

    if uploaded_files:
        st.write(f"已上传 {len(uploaded_files)} 个文件:")
        for f in uploaded_files:
            size_mb = f.size / 1024 / 1024
            st.write(f"  - {f.name} ({size_mb:.1f} MB)")

with col2:
    # 操作按钮
    st.subheader("🚀 操作")

    if not uploaded_files:
        st.button("开始转换", disabled=True)
    elif st.session_state.processing:
        st.button("处理中...", disabled=True)
    else:
        if st.button("开始转换", type="primary", use_container_width=True):
            if not output_dir:
                st.error("请设置输出目录")
            else:
                st.session_state.processing = True
                st.session_state.logs = []
                st.session_state.results = []

                # 初始化断点相关 session_state
                if "checkpoint_manager" not in st.session_state:
                    st.session_state.checkpoint_manager = CheckpointManager()
                if "resume_choices" not in st.session_state:
                    st.session_state.resume_choices = {}
                if "pending_checkpoints" not in st.session_state:
                    st.session_state.pending_checkpoints = []  # 待确认的文件

                checkpoint_manager = st.session_state.checkpoint_manager

                # 保存上传的文件
                os.makedirs("temp_uploads", exist_ok=True)
                saved_files = []

                for f in uploaded_files:
                    # 验证文件
                    try:
                        validate_uploaded_file(f)
                    except ValueError as e:
                        st.error(f"文件 {f.name} 验证失败: {str(e)}")
                        continue

                    # 清理文件名，只保留安全字符
                    safe_name = os.path.basename(f.name)
                    path = os.path.join("temp_uploads", safe_name)

                    # 检查是否有未完成的处理任务
                    resume_action = st.session_state.resume_choices.get(safe_name)

                    if checkpoint_manager.has_checkpoint(safe_name) and resume_action is None:
                        # 第一次检测到断点，显示选择对话框
                        st.warning(f"检测到未完成的处理任务: {safe_name}")
                        col_resume, col_restart = st.columns(2)
                        with col_resume:
                            if st.button(f"继续处理", key=f"resume_{safe_name}"):
                                # 立即保存文件
                                with open(path, "wb") as out:
                                    out.write(f.read())
                                saved_files.append((path, safe_name))
                                st.session_state.resume_choices[safe_name] = True
                                st.rerun()
                        with col_restart:
                            if st.button(f"重新开始", key=f"restart_{safe_name}"):
                                checkpoint_manager.delete_checkpoint(safe_name)
                                # 立即保存文件
                                with open(path, "wb") as out:
                                    out.write(f.read())
                                saved_files.append((path, safe_name))
                                st.session_state.resume_choices[safe_name] = False
                                st.success(f"已清除 {safe_name} 的断点，将重新开始处理")
                        # 用户还没做选择，不保存文件也不继续
                        continue
                    elif resume_action is True:
                        # 用户选择继续处理，保留断点
                        with open(path, "wb") as out:
                            out.write(f.read())
                        saved_files.append((path, safe_name))
                    elif resume_action is False:
                        # 用户选择重新开始（断点已删除）
                        with open(path, "wb") as out:
                            out.write(f.read())
                        saved_files.append((path, safe_name))
                    else:
                        # 没有断点，正常保存
                        with open(path, "wb") as out:
                            out.write(f.read())
                        saved_files.append((path, safe_name))

                # 如果有待确认的文件，先不处理
                if st.session_state.pending_checkpoints:
                    st.session_state.processing = False
                    st.stop()

                if not saved_files:
                    st.warning("没有可处理的文件")
                    st.session_state.processing = False
                    st.stop()

                # 创建处理器
                processor = VideoProcessor(
                    model_name=model,
                    output_dir=output_dir,
                    split_size=split_size,
                    progress_callback=progress_callback
                )

                # 批量处理
                for i, (video_path, video_name) in enumerate(saved_files):
                    try:
                        # 使用自定义文件名或默认
                        fname = custom_filename.strip() if custom_filename.strip() else None
                        # 如果有多个文件且没有自定义名，使用"原名_序号"
                        if len(saved_files) > 1 and fname:
                            fname = f"{fname}_{i + 1}"
                        elif len(saved_files) > 1:
                            base = os.path.splitext(video_name)[0]
                            fname = f"{base}_{i + 1}"

                        log(f"开始处理: {video_name}")
                        result = processor.process_video(video_path, custom_filename=fname)

                        if isinstance(result, list):
                            for r in result:
                                st.session_state.results.append(("success", r))
                                log(f"✅ 完成: {r}")
                        else:
                            st.session_state.results.append(("success", result))
                            log(f"✅ 完成: {result}")

                    except Exception as e:
                        st.session_state.results.append(("error", str(e)))
                        log(f"❌ 失败: {str(e)}")

                # 清理上传文件
                for path, _ in saved_files:
                    try:
                        os.remove(path)
                    except OSError:
                        pass

                st.session_state.processing = False
                st.rerun()

# 日志区域
st.divider()
st.subheader("📝 日志")

if st.session_state.logs:
    log_container = st.container(height=300, border=True)
    with log_container:
        for log_msg in st.session_state.logs:
            st.text(log_msg)
else:
    st.info("日志将显示在这里...")

# 结果区域
if st.session_state.results:
    st.divider()
    st.subheader("📋 处理结果")

    for status, path in st.session_state.results:
        if status == "success":
            st.success(f"✅ {path}")
        else:
            st.error(f"❌ {path}")

# 底部信息
st.divider()
st.caption("""
**提示**:
- 首次使用会下载 Whisper 模型，请耐心等待
- 建议使用 small 模型，M4 16GB 内存足够
- 视频会自动分段处理(每段30分钟)以保证识别质量
- 大 SRT 文件会自动切分
""")
