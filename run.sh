#!/bin/bash

# ═══════════════════════════════════════════════════════════════════════════════
# Hunter AI 内容工厂 - Mac/Linux 零配置一键启动脚本
#
# 特点：
# - 空白电脑运行即可，无需任何预装环境
# - 自动下载并安装 uv 包管理器（到项目目录）
# - 自动下载并安装 Python 3.12（由 uv 管理）
# - 自动安装项目依赖
# - 启动 Gradio Web UI 并自动打开浏览器
#
# 使用方法（无需 chmod，直接运行）：
#   bash run.sh
#
# 或者双击运行（Mac 终端）
#
# GitHub: https://github.com/Pangu-Immortal/hunter-ai-content-factory
# Author: Pangu-Immortal
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 切换到脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 本地 uv 路径
LOCAL_UV="$SCRIPT_DIR/.local/uv"
UV_EXE="$LOCAL_UV/uv"

# 打印带颜色的消息
print_header() {
    echo ""
    echo -e "${MAGENTA}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║                                                           ║${NC}"
    echo -e "${MAGENTA}║     ${CYAN}🦅 Hunter AI 内容工厂${MAGENTA}                                 ║${NC}"
    echo -e "${MAGENTA}║                                                           ║${NC}"
    echo -e "${MAGENTA}║     ${NC}一键生成高质量公众号文章的 AI 工作流${MAGENTA}                  ║${NC}"
    echo -e "${MAGENTA}║                                                           ║${NC}"
    echo -e "${MAGENTA}║     ${YELLOW}首次运行需要下载环境，请耐心等待...${MAGENTA}                   ║${NC}"
    echo -e "${MAGENTA}║                                                           ║${NC}"
    echo -e "${MAGENTA}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo -e "${BLUE}[$1]${NC} $2"
}

print_success() {
    echo -e "   ${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "   ${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "   ${RED}❌ $1${NC}"
}

print_info() {
    echo -e "   ${CYAN}⏳ $1${NC}"
}

print_header

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: 检查/安装 uv（本地安装，不污染系统）
# ─────────────────────────────────────────────────────────────────────────────
print_step "1/6" "检查 uv 包管理器..."

# 首先检查本地 uv
if [ -f "$UV_EXE" ]; then
    print_success "本地 uv 已存在"
# 检查系统 uv
elif command -v uv &> /dev/null; then
    print_success "系统 uv 已安装"
    UV_EXE="uv"
else
    # 下载并安装 uv 到本地目录
    print_info "正在下载 uv 包管理器..."
    echo "       （首次运行，请稍候约 1-2 分钟）"

    # 创建本地目录
    mkdir -p "$LOCAL_UV"

    # 检测系统架构
    ARCH=$(uname -m)
    OS=$(uname -s)

    if [ "$OS" = "Darwin" ]; then
        if [ "$ARCH" = "arm64" ]; then
            UV_URL="https://github.com/astral-sh/uv/releases/latest/download/uv-aarch64-apple-darwin.tar.gz"
        else
            UV_URL="https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-apple-darwin.tar.gz"
        fi
    else
        if [ "$ARCH" = "aarch64" ]; then
            UV_URL="https://github.com/astral-sh/uv/releases/latest/download/uv-aarch64-unknown-linux-gnu.tar.gz"
        else
            UV_URL="https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz"
        fi
    fi

    # 下载并解压
    if command -v curl &> /dev/null; then
        curl -sL "$UV_URL" | tar xz -C "$LOCAL_UV" --strip-components=1
    elif command -v wget &> /dev/null; then
        wget -qO- "$UV_URL" | tar xz -C "$LOCAL_UV" --strip-components=1
    else
        print_error "需要 curl 或 wget 来下载 uv"
        echo "请安装后重试："
        echo "  Mac: brew install curl"
        echo "  Ubuntu: sudo apt install curl"
        exit 1
    fi

    if [ ! -f "$UV_EXE" ]; then
        print_error "uv 下载失败！"
        echo "请检查网络连接，或手动下载："
        echo "https://github.com/astral-sh/uv/releases"
        exit 1
    fi

    chmod +x "$UV_EXE"
    print_success "uv 下载完成"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: 检查/安装 Python（由 uv 管理）
# ─────────────────────────────────────────────────────────────────────────────
echo ""
print_step "2/6" "检查 Python 环境..."

# 使用 uv 检查并安装 Python
if ! "$UV_EXE" python find 3.12 &> /dev/null; then
    print_info "正在下载 Python 3.12..."
    echo "       （首次运行，请稍候约 2-3 分钟）"
    "$UV_EXE" python install 3.12 --quiet

    if [ $? -ne 0 ]; then
        print_error "Python 下载失败！"
        echo "请检查网络连接"
        exit 1
    fi
fi

print_success "Python 3.12 就绪"

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: 检查配置文件
# ─────────────────────────────────────────────────────────────────────────────
echo ""
print_step "3/6" "检查配置文件..."

if [ ! -f "config.yaml" ]; then
    if [ -f "config.example.yaml" ]; then
        print_info "创建配置文件..."
        cp config.example.yaml config.yaml
        print_success "已创建 config.yaml"
        echo ""
        echo -e "${YELLOW}    ════════════════════════════════════════════════════════════${NC}"
        echo -e "${YELLOW}    ⚠️ 重要提示：首次运行请先配置 API Key！${NC}"
        echo ""
        echo "       1. 编辑项目目录下的 config.yaml"
        echo "       2. 填写 gemini.api_key（必填，从 Google AI Studio 获取）"
        echo "       3. 其他配置可选填"
        echo -e "${YELLOW}    ════════════════════════════════════════════════════════════${NC}"
        echo ""
    else
        print_warning "未找到配置文件模板"
    fi
else
    print_success "config.yaml 已存在"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: 安装依赖
# ─────────────────────────────────────────────────────────────────────────────
echo ""
print_step "4/6" "安装项目依赖..."

# 使用 uv 同步依赖（强制使用 Python 3.12）
if ! "$UV_EXE" sync --python 3.12 --python-preference only-managed --quiet 2>/dev/null; then
    print_info "首次安装依赖，请稍候..."
    "$UV_EXE" sync --python 3.12 --python-preference only-managed

    if [ $? -ne 0 ]; then
        print_error "依赖安装失败！"
        echo "请检查网络连接"
        exit 1
    fi
fi

print_success "依赖已安装"

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: 安装 Playwright 浏览器（用于小红书采集）
# ─────────────────────────────────────────────────────────────────────────────
echo ""
print_step "5/6" "检查浏览器驱动..."

# 检查是否已安装 Playwright 浏览器
if [ ! -d "$HOME/.cache/ms-playwright" ] && [ ! -d "$SCRIPT_DIR/.playwright" ]; then
    print_info "首次安装浏览器驱动，请稍候..."
    "$UV_EXE" run --python 3.12 --python-preference only-managed playwright install chromium --with-deps 2>/dev/null || \
    "$UV_EXE" run --python 3.12 --python-preference only-managed playwright install chromium 2>/dev/null || true
fi

print_success "浏览器驱动就绪"

# ─────────────────────────────────────────────────────────────────────────────
# Step 6: 启动 Gradio
# ─────────────────────────────────────────────────────────────────────────────
echo ""
print_step "6/6" "启动 Web UI..."

# 获取本机 IP
if command -v hostname &> /dev/null; then
    LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || ipconfig getifaddr en0 2>/dev/null || echo "你的IP")
else
    LOCAL_IP="你的IP"
fi

echo ""
echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "   ${GREEN}🚀 Hunter AI 正在启动...${NC}"
echo ""
echo -e "   本地访问:    ${CYAN}http://localhost:7860${NC}"
echo -e "   局域网访问:  ${CYAN}http://${LOCAL_IP}:7860${NC}"
echo -e "   外链分享:    启动后会显示公网链接"
echo ""
echo -e "   ${YELLOW}⚡ 浏览器将自动打开，如果没有请手动访问上述地址${NC}"
echo ""
echo -e "   ${YELLOW}按 Ctrl+C 停止服务${NC}"
echo ""
echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════════════════${NC}"
echo ""

# 自动打开浏览器（后台延迟执行）
(sleep 5 && {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open "http://localhost:7860"
    elif command -v xdg-open &> /dev/null; then
        xdg-open "http://localhost:7860"
    fi
} &) 2>/dev/null

# 启动 Gradio（使用 Python 3.12）
"$UV_EXE" run --python 3.12 --python-preference only-managed python -m src.gradio_launcher

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "   服务已停止"
echo "════════════════════════════════════════════════════════════════"
