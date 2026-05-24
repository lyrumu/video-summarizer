#!/bin/bash
# Video Summarizer — 一键安装脚本
# 用法: bash <(curl -s https://raw.githubusercontent.com/lyrumu/video-summarizer/main/install.sh)

set -e

echo "🎬 Video Summarizer 安装中..."
echo ""

# 检查 Python
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "❌ 未找到 Python3，请先安装: https://www.python.org/downloads/"
    exit 1
fi

PYVER=$($PYTHON --version 2>&1)
echo "✅ 检测到: $PYVER"

# 检查 pip
if ! $PYTHON -m pip --version &>/dev/null; then
    echo "📦 安装 pip..."
    curl -sS https://bootstrap.pypa.io/get-pip.py | $PYTHON
fi

# 升级 pip（pyproject.toml 需要较新版本）
echo "📦 升级 pip..."
$PYTHON -m pip install --user --upgrade pip -q 2>/dev/null
$PYTHON -m pip install --user --upgrade setuptools wheel -q 2>/dev/null

# 检查 ffmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo "🎵 安装 ffmpeg（音频处理需要）..."
    if command -v apt &>/dev/null; then
        sudo apt install -y ffmpeg
    elif command -v brew &>/dev/null; then
        brew install ffmpeg
    elif command -v pacman &>/dev/null; then
        sudo pacman -S ffmpeg
    else
        echo "⚠ 请手动安装 ffmpeg"
    fi
else
    echo "✅ ffmpeg 已安装"
fi

# 安装 vidsum
echo ""
echo "📦 安装 vidsum..."
$PYTHON -m pip install --user vidsum 2>/dev/null || {
    # 如果还没上传 PyPI，从 GitHub 安装
    echo "  从 GitHub 安装开发版..."
    $PYTHON -m pip install --user git+https://github.com/lyrumu/video-summarizer.git
}

# 验证安装
echo ""
if $PYTHON -m video_summarizer --help &>/dev/null; then
    echo "✅ 安装成功！"
    echo ""
    echo "启动方式:"
    echo "  video-summarizer              # 打开 Web 界面"
    echo "  python3 -m video_summarizer   # 同上（如果命令找不到）"
    echo ""
    echo "首次使用:"
    echo "  1. 浏览器打开 http://127.0.0.1:8020"
    echo "  2. 进入 /config 配置 API Key"
    echo "  3. 贴视频链接开始总结"
else
    echo "⚠ 安装完成，但命令未添加到 PATH"
    echo "  请尝试: python3 -m video_summarizer"
fi
