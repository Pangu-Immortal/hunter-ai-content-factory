"""
摆渡人AI系统 - 全自动生产 Tab

五平台采集 → AI 分析 → 选题生成 → 文章创作 → 公众号排版，全流程自动化
"""

import asyncio
import gradio as gr
from ..handlers import run_auto_template


def create_auto_tab():
    """创建全自动生产 Tab"""
    with gr.Tab("🚀 全自动生产", id="auto"):
        gr.Markdown("""
        **五平台采集 → AI 分析 → 选题生成 → 文章创作 → 公众号排版，全流程自动化**

        📊 输出格式：AI 生活黑客风格文章 | 📁 保存位置：`output/日期/文章标题/`

        🔄 执行流程：`Topic → Research → Structure → Write → Package → Publish`
        """)

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### ⚙️ 参数设置")
                auto_niche = gr.Textbox(
                    label="📌 细分领域",
                    placeholder="AI技术、Python开发...",
                    value="AI技术",
                    info="AI 会围绕此领域生成内容"
                )
                gr.Markdown("""
                **文章结构**：
                - 💔 崩溃瞬间（生动描述用户遇到的"人工智障"时刻）
                - 🔧 魔法修补（解释为什么 AI 会犯错 + 解决方案）
                - 🎁 咒语交付（可直接复制的 Prompt/指令）
                """)
                auto_dry_run = gr.Checkbox(
                    label="🧪 试运行模式（不推送）",
                    value=True
                )
                auto_run_btn = gr.Button("🚀 全自动运行", variant="primary", size="lg")

            with gr.Column(scale=2):
                gr.Markdown("### 📋 执行日志")
                auto_log_output = gr.Markdown()

        gr.Markdown("### 📝 文章预览")
        auto_article_output = gr.Textbox(label="生成的文章", lines=15)

        auto_run_btn.click(
            fn=lambda n, d: asyncio.run(run_auto_template(n, d)),
            inputs=[auto_niche, auto_dry_run],
            outputs=[auto_log_output, auto_article_output]
        )
