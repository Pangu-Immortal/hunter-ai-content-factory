"""
摆渡人AI系统 - 内容审核 Tab

检查文章违禁词，清理 AI 生成痕迹
"""

import gradio as gr
from ..handlers import run_content_check, run_content_clean


def create_check_tab():
    """创建内容审核 Tab"""
    with gr.Tab("🔍 内容审核", id="check"):
        gr.Markdown("""
        检查文章违禁词，清理 AI 生成痕迹。支持：标题党词汇、虚假宣传词、AI 痕迹词。
        """)

        content_input = gr.Textbox(
            label="📝 待检查内容",
            placeholder="粘贴你的文章内容...",
            lines=8
        )

        with gr.Row():
            check_btn = gr.Button("🔍 检查违禁词", variant="secondary")
            clean_btn = gr.Button("🧹 清理 AI 痕迹", variant="primary")

        check_output = gr.Markdown()
        cleaned_output = gr.Textbox(label="📝 处理后内容", lines=8)

        check_btn.click(fn=run_content_check, inputs=[content_input], outputs=[check_output, cleaned_output])
        clean_btn.click(fn=run_content_clean, inputs=[content_input], outputs=[check_output, cleaned_output])
