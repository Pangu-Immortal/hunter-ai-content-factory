"""
摆渡人AI系统 - 热点快报 Tab

同步采集多平台资讯，生成今日资讯速览
"""

import asyncio
import gradio as gr
from ..handlers import run_news_template


def create_news_tab():
    """创建热点快报 Tab"""
    with gr.Tab("📰 热点快报", id="news"):
        gr.Markdown("""
        **同步采集微博/知乎/抖音/B站/HackerNews 五大平台，生成今日资讯速览**

        📊 输出格式：资讯快报文章 | 📁 保存位置：`output/日期/articles/`

        > ⚠️ 部分平台需要配置 Cookies
        """)

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### ⚙️ 采集平台")
                gr.Markdown("""
                | 平台 | 内容类型 |
                |------|----------|
                | HackerNews | 技术热点 |
                | Twitter | 行业动态 |
                | Reddit | 社区讨论 |
                | GitHub | 开源趋势 |
                | 小红书 | 生活热点 |
                """)
                news_dry_run = gr.Checkbox(
                    label="🧪 试运行模式（不推送）",
                    value=True
                )
                news_run_btn = gr.Button("📰 生成快报", variant="primary", size="lg")

            with gr.Column(scale=2):
                gr.Markdown("### 📋 执行日志")
                news_log_output = gr.Markdown()

        gr.Markdown("### 📝 快报预览")
        news_article_output = gr.Textbox(label="资讯快报", lines=15)

        news_run_btn.click(
            fn=lambda d: asyncio.run(run_news_template(d)),
            inputs=[news_dry_run],
            outputs=[news_log_output, news_article_output]
        )
