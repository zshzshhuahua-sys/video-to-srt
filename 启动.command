#!/bin/zsh
# 一键启动视频转 SRT 字幕工具

# 获取脚本所在目录
SCRIPT_DIR="${0:a:h}"
cd "$SCRIPT_DIR"

# 检查虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "检测到未创建虚拟环境，是否现在创建? (y/n)"
    read answer
    if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    else
        echo "请手动激活环境后运行: streamlit run app.py"
        read -p "按 Enter 键退出..."
        exit 1
    fi
fi

# 检查依赖
echo "检查依赖..."
python3 -c "import streamlit" 2>/dev/null || {
    echo "缺少依赖，正在安装..."
    pip install -r requirements.txt
}

# 启动
echo ""
echo "正在启动应用..."
echo "如浏览器未自动打开，请手动访问: http://localhost:8501"
echo ""
streamlit run app.py

# 保持窗口打开(可选)
read -p "按 Enter 键退出..."
