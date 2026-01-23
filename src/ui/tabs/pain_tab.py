"""
Hunter AI - 痛点诊断 Tab

全网扫描用户真实吐槽，AI 分析痛点并生成解决方案型爆文选题
"""

import asyncio
import gradio as gr
from ..handlers import run_pain_template


def create_pain_tab():
    """创建痛点诊断 Tab"""
    with gr.Tab("💊 痛点诊断", id="pain"):
        gr.Markdown("""
        **全网扫描用户真实吐槽，AI 分析痛点并生成解决方案型爆文选题**

        📊 输出格式：Markdown 诊断报告 | 📁 保存位置：`output/日期/reports/`

        > ⚠️ 需要配置 Twitter Cookies (`data/cookies.json`)
        """)

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### ⚙️ 参数设置")
                gr.Markdown("""
                **扫描平台**: Twitter + Reddit

                **目标产品**: ChatGPT、Claude、DeepSeek 等 AI 产品

                **痛点分类**: 性能/准确性/稳定性/功能/体验/API
                """)
                pain_dry_run = gr.Checkbox(
                    label="🧪 试运行模式（不推送）",
                    value=True
                )
                pain_run_btn = gr.Button("💊 开始诊断", variant="primary", size="lg")

            with gr.Column(scale=2):
                gr.Markdown("### 📋 执行日志")
                pain_log_output = gr.Markdown()

        gr.Markdown("### 📝 诊断报告预览")
        pain_article_output = gr.Textbox(label="诊断报告", lines=15)

        pain_run_btn.click(
            fn=lambda d: asyncio.run(run_pain_template(d)),
            inputs=[pain_dry_run],
            outputs=[pain_log_output, pain_article_output]
        )
