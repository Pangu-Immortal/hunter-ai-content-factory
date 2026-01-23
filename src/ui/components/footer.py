"""
摆渡人AI系统 - 底部页脚组件
"""

import gradio as gr


def create_footer():
    """创建底部页脚"""
    gr.HTML("""
    <div style="text-align: center; padding: 20px; margin-top: 30px; border-top: 2px solid var(--brand-secondary, #ffb6c1);">
        <p style="color: var(--text-muted, #999); margin: 0;">Made with 💖 by Pangu-Immortal</p>
        <p style="color: var(--text-hint, #ccc); font-size: 0.9em; margin: 5px 0 0 0;">
            摆渡人AI系统 v2.0 |
            <a href="https://github.com/Pangu-Immortal/hunter-ai-content-factory" style="color: var(--brand-link, #ff69b4);">GitHub</a>
        </p>
    </div>
    """)


def create_divider():
    """创建分隔线"""
    gr.HTML("""
    <div style="height: 3px; background: linear-gradient(90deg, transparent, var(--brand-secondary, #ffb6c1), transparent); margin: 30px 0; border-radius: 3px;"></div>
    """)
