"""
摆渡人AI系统 - 小红书种草 Tab

一键采集小红书爆款笔记，AI 改写为公众号风格的种草推荐文
"""

import asyncio

import gradio as gr

from ..handlers import run_xhs_template


def create_xhs_tab():
    """创建小红书种草 Tab"""
    with gr.Tab("📕 小红书种草", id="xhs"):
        gr.Markdown("""
        **一键采集小红书爆款笔记，AI 改写为公众号风格的种草推荐文**

        📊 输出格式：种草/测评文章 | 📁 保存位置：`output/日期/articles/`

        > ⚠️ 需要配置小红书 Cookies (`config.yaml` → `xiaohongshu.cookies`)
        """)

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### ⚙️ 参数设置")
                xhs_keyword = gr.Textbox(
                    label="🔍 搜索关键词", placeholder="数码好物、美妆测评...", value="", info="留空则采集热门笔记"
                )
                xhs_dry_run = gr.Checkbox(label="🧪 试运行模式（不推送）", value=True)
                xhs_run_btn = gr.Button("📕 开始采集", variant="primary", size="lg")

            with gr.Column(scale=2):
                gr.Markdown("### 📋 执行日志")
                xhs_log_output = gr.Markdown()

        gr.Markdown("### 📝 种草文预览")
        xhs_article_output = gr.Textbox(label="种草文章", lines=15)

        xhs_run_btn.click(
            fn=lambda k, d: asyncio.run(run_xhs_template(k, d)),
            inputs=[xhs_keyword, xhs_dry_run],
            outputs=[xhs_log_output, xhs_article_output],
        )
