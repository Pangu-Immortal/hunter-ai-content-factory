"""
Hunter AI 内容工厂 - Gradio Web UI 启动器

功能：
- 统一的 Web UI 启动入口
- 模块化 UI 架构（独立于 gradio_app.py）
- 支持深浅主题自动切换（跟随系统）

使用方法：
    uv run python -m src.gradio_launcher  # 启动 Web UI

备用启动（使用 gradio_app.py 单文件版本）：
    uv run python -m src.gradio_app
"""

import os
import socket
import gradio as gr
from rich.console import Console

# 终端输出
console = Console()

# JavaScript 代码：Tab 溢出按钮移除 + 主题动态切换监听
CUSTOM_JS = """
// ═══════════════════════════════════════════════════════════════════════════
// 主题动态切换监听 - 系统深浅主题变化时自动响应
// ═══════════════════════════════════════════════════════════════════════════

// 深色主题颜色配置
const DARK_THEME = {
    bgPrimary: '#1e2430',
    bgSecondary: '#252b37',
    bgTertiary: '#2a3142',
    textPrimary: '#d4dae5',
    textSecondary: '#a8b5c8',
    textMuted: '#8b9bb4',
    borderColor: '#3a4555',
    accentColor: '#5cb3cc'
};

// 应用主题
function applyTheme() {
    const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = isDark ? 'dark' : 'light';

    // 设置 data-theme 属性到多个元素
    document.documentElement.setAttribute('data-theme', theme);
    document.body.setAttribute('data-theme', theme);

    // 找到 Gradio 容器并设置属性
    const container = document.querySelector('.gradio-container');
    if (container) {
        container.setAttribute('data-theme', theme);
        container.style.transition = 'background 0.3s ease, color 0.3s ease';
    }

    // 如果是深色模式，直接通过 JavaScript 强制应用关键样式
    if (isDark) {
        applyDarkStyles();
    } else {
        removeDarkStyles();
    }

    console.log('[Hunter AI] 主题切换:', isDark ? '深色模式' : '浅色模式');
}

// 强制应用深色样式（作为 CSS 的后备方案）
function applyDarkStyles() {
    // 设置 CSS 变量
    document.documentElement.style.setProperty('--bg-primary', DARK_THEME.bgPrimary);
    document.documentElement.style.setProperty('--bg-secondary', DARK_THEME.bgSecondary);
    document.documentElement.style.setProperty('--bg-tertiary', DARK_THEME.bgTertiary);
    document.documentElement.style.setProperty('--text-primary', DARK_THEME.textPrimary);
    document.documentElement.style.setProperty('--text-secondary', DARK_THEME.textSecondary);
    document.documentElement.style.setProperty('--text-muted', DARK_THEME.textMuted);
    document.documentElement.style.setProperty('--border-color', DARK_THEME.borderColor);
    document.documentElement.style.setProperty('--accent-color', DARK_THEME.accentColor);

    // 直接设置关键元素的背景色
    document.body.style.background = DARK_THEME.bgPrimary;
    document.body.style.color = DARK_THEME.textPrimary;

    const container = document.querySelector('.gradio-container');
    if (container) {
        container.style.background = DARK_THEME.bgPrimary;
        container.style.color = DARK_THEME.textPrimary;
    }

    // 设置所有面板和块的背景
    document.querySelectorAll('.block, .panel, .form, .gr-box, .gr-panel, .gr-form, .gr-block, .tabs, .tabitem').forEach(el => {
        el.style.background = DARK_THEME.bgPrimary;
    });

    // 设置输入框样式
    document.querySelectorAll('input, textarea, select').forEach(el => {
        el.style.background = DARK_THEME.bgSecondary;
        el.style.color = DARK_THEME.textSecondary;
        el.style.borderColor = DARK_THEME.borderColor;
    });

    // 设置 Tab 容器样式（胶囊式）
    document.querySelectorAll('.tab-nav, div[role="tablist"]').forEach(el => {
        el.style.background = DARK_THEME.bgSecondary;
        el.style.borderRadius = '12px';
        el.style.padding = '4px';
        el.style.border = 'none';
    });

    // 设置 Tab 按钮样式（胶囊式）
    document.querySelectorAll('.tab-nav button, [role="tab"]').forEach(el => {
        el.style.borderRadius = '8px';
        el.style.border = 'none';
        if (!el.classList.contains('selected') && el.getAttribute('aria-selected') !== 'true') {
            el.style.color = '#b8c4d6';
            el.style.background = 'transparent';
        } else {
            el.style.background = DARK_THEME.accentColor;
            el.style.color = '#ffffff';
        }
    });

    // 设置普通按钮样式（渐变彩色 - 蓝紫渐变）
    document.querySelectorAll('button:not([role="tab"]):not(.primary)').forEach(el => {
        // 排除 Tab 按钮
        if (!el.closest('.tab-nav') && !el.closest('[role="tablist"]')) {
            el.style.background = 'linear-gradient(135deg, #7c8ff8 0%, #667eea 50%, #5a67d8 100%)';
            el.style.color = '#ffffff';
            el.style.border = 'none';
            el.style.borderRadius = '8px';
            el.style.boxShadow = '0 4px 20px rgba(124, 143, 248, 0.35)';
        }
    });

    // 设置 Primary 按钮样式（渐变彩色 - 粉色渐变）
    document.querySelectorAll('button.primary, .primary').forEach(el => {
        el.style.background = 'linear-gradient(135deg, #f06292 0%, #ec407a 50%, #e91e63 100%)';
        el.style.color = '#ffffff';
        el.style.border = 'none';
        el.style.borderRadius = '8px';
        el.style.boxShadow = '0 4px 20px rgba(240, 98, 146, 0.4)';
    });
}

// 移除深色样式（恢复浅色模式）
function removeDarkStyles() {
    // 移除 CSS 变量覆盖
    document.documentElement.style.removeProperty('--bg-primary');
    document.documentElement.style.removeProperty('--bg-secondary');
    document.documentElement.style.removeProperty('--bg-tertiary');
    document.documentElement.style.removeProperty('--text-primary');
    document.documentElement.style.removeProperty('--text-secondary');
    document.documentElement.style.removeProperty('--text-muted');
    document.documentElement.style.removeProperty('--border-color');
    document.documentElement.style.removeProperty('--accent-color');

    // 移除直接设置的样式
    document.body.style.background = '';
    document.body.style.color = '';

    const container = document.querySelector('.gradio-container');
    if (container) {
        container.style.background = '';
        container.style.color = '';
    }

    document.querySelectorAll('.block, .panel, .form, .gr-box, .gr-panel, .gr-form, .gr-block, .tabs, .tabitem').forEach(el => {
        el.style.background = '';
    });

    document.querySelectorAll('input, textarea, select').forEach(el => {
        el.style.background = '';
        el.style.color = '';
        el.style.borderColor = '';
    });

    // 重置 Tab 容器样式（保留胶囊式，只重置颜色）
    document.querySelectorAll('.tab-nav, div[role="tablist"]').forEach(el => {
        el.style.background = '';
    });

    // 重置 Tab 按钮样式
    document.querySelectorAll('.tab-nav button, [role="tab"]').forEach(el => {
        el.style.color = '';
        el.style.background = '';
    });

    // 重置普通按钮样式（让 CSS 接管浅色主题渐变）
    document.querySelectorAll('button:not([role="tab"])').forEach(el => {
        if (!el.closest('.tab-nav') && !el.closest('[role="tablist"]')) {
            el.style.background = '';
            el.style.color = '';
            el.style.border = '';
            el.style.boxShadow = '';
        }
    });
}

// 监听系统主题变化
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyTheme);

// 页面加载时应用主题
applyTheme();

// Gradio 可能会延迟渲染，所以多次尝试应用主题
setTimeout(applyTheme, 100);
setTimeout(applyTheme, 500);
setTimeout(applyTheme, 1000);

// 监听 DOM 变化，在 Gradio 重新渲染后重新应用主题
const themeObserver = new MutationObserver(() => {
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        applyDarkStyles();
    }
});
themeObserver.observe(document.body, { childList: true, subtree: true });

// ═══════════════════════════════════════════════════════════════════════════
// Tab 溢出按钮移除
// ═══════════════════════════════════════════════════════════════════════════
function removeTabOverflowButtons() {
    // 移除所有非 Tab 按钮（溢出菜单按钮）
    const tabLists = document.querySelectorAll('div[role="tablist"], .tab-nav');
    tabLists.forEach(tabList => {
        const buttons = tabList.querySelectorAll('button');
        buttons.forEach(btn => {
            if (!btn.hasAttribute('role') || btn.getAttribute('role') !== 'tab') {
                btn.style.display = 'none';
                btn.style.visibility = 'hidden';
                btn.style.width = '0';
                btn.style.height = '0';
                btn.style.position = 'absolute';
                btn.style.left = '-9999px';
            }
        });
        // 强制显示所有 Tab
        tabList.style.flexWrap = 'wrap';
        tabList.style.overflow = 'visible';
    });
}

// 页面加载后执行
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', removeTabOverflowButtons);
} else {
    removeTabOverflowButtons();
}

// 监听 DOM 变化，持续移除溢出按钮
const tabObserver = new MutationObserver(removeTabOverflowButtons);
tabObserver.observe(document.body, { childList: true, subtree: true });

// 定时检查（备用方案）
setInterval(removeTabOverflowButtons, 1000);
"""


def main():
    """启动 Gradio 应用（模块化版本）"""
    console.print("[bold magenta]🦅 启动 Hunter AI Web UI...[/bold magenta]\n")

    # 使用模块化 UI（独立于 gradio_app.py）
    from src.ui import create_app

    app = create_app()

    # 获取局域网IP地址
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"

    console.print("[cyan]本地访问: http://127.0.0.1:7860[/cyan]")
    console.print(f"[cyan]局域网访问: http://{local_ip}:7860[/cyan]")
    console.print("[cyan]外网分享: 启动后显示公网链接[/cyan]\n")

    # 设置环境变量避免代理干扰
    os.environ['NO_PROXY'] = 'localhost,127.0.0.1,0.0.0.0'
    os.environ['no_proxy'] = 'localhost,127.0.0.1,0.0.0.0'

    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        show_error=True,
        inbrowser=False,
        js=CUSTOM_JS,    # 注入 JavaScript 移除溢出按钮
        # CSS 已在 gr.Blocks() 中传递，深浅主题跟随系统自动切换
    )


if __name__ == "__main__":
    main()
