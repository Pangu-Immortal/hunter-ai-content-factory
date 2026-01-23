"""
Hunter AI - 顶部标题组件
"""

import gradio as gr


def create_header():
    """创建顶部标题"""
    gr.HTML("""
    <!-- 顶部标题 -->
    <div style="text-align: center; padding: 25px 20px 20px 20px;">
        <h1 style="font-size: 2.5em; margin: 0; color: var(--brand-primary, #e91e63); text-shadow: 2px 2px 4px var(--brand-shadow, rgba(233,30,99,0.2));">
            🦅 Hunter AI 内容工厂
        </h1>
        <p style="font-size: 1.1em; color: var(--text-muted, #666); margin: 10px 0 0 0;">
            一键生成高质量公众号文章的 AI 工作流
        </p>
    </div>
    """)
