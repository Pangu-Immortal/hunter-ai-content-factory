"""
摆渡人AI系统 - GitHub 爆款 Tab

自动抓取 GitHub 热门项目，AI 生成深度技术解读文章
"""

import asyncio
import gradio as gr
from ..handlers import run_github_template


def create_github_tab():
    """创建 GitHub 爆款 Tab"""
    with gr.Tab("🔥 GitHub 爆款", id="github"):
        gr.Markdown("""
        **自动抓取 GitHub 热门项目，AI 生成深度技术解读文章，一键产出公众号爆款**

        📊 自定义文章结构 | 📁 保存位置：`output/日期/文章标题/`
        """)

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### ⚙️ 参数设置")
                github_keyword_input = gr.Textbox(
                    label="🔍 搜索关键词",
                    value="AI",
                    placeholder="输入关键词，如: AI、LLM、RAG、Agent、机器学习...",
                    info="筛选 GitHub 项目的品类/功能/技术方向"
                )
                gr.Markdown("""
                <div style="background: var(--tip-yellow-bg, rgba(255, 200, 0, 0.15)); padding: 8px 12px; border-radius: 6px; margin: 5px 0; font-size: 12px; border: 1px solid var(--tip-yellow-border, rgba(255, 200, 0, 0.4)); color: var(--tip-yellow-text, #ffd700);">
                💡 <b>Tips</b>: 关键词决定搜索的项目类型<br/>
                • <b>AI</b> - 人工智能相关项目<br/>
                • <b>LLM/Agent</b> - 大模型/智能体项目<br/>
                • <b>RAG</b> - 检索增强生成项目<br/>
                • <b>Web/React/Vue</b> - 前端框架项目<br/>
                • <b>Rust/Go</b> - 特定语言项目<br/>
                • 支持多关键词，用空格分隔
                </div>
                """)
                github_min_stars_input = gr.Slider(
                    label="🌟 最小 Stars 数",
                    minimum=50, maximum=5000, value=200, step=50,
                    info="过滤低于此 Stars 数的项目"
                )

                gr.Markdown("### 📝 文章结构")
                github_brief_count = gr.Slider(
                    label="📋 项目简介数量",
                    minimum=2, maximum=10, value=2, step=1,
                    info="快速介绍的项目数量（最少2个，每个约300-500字）"
                )
                github_deep_count = gr.Slider(
                    label="🔬 深度解读数量",
                    minimum=1, maximum=5, value=1, step=1,
                    info="详细分析的项目数量（最少1个，每个约1500-2000字）"
                )
                github_min_words = gr.Slider(
                    label="📏 文章最小字数",
                    minimum=1500, maximum=8000, value=3500, step=500,
                    info="生成文章的最低字数要求"
                )
                gr.Markdown("""
                <div style="background: var(--tip-cyan-bg, rgba(0, 255, 255, 0.1)); padding: 8px 12px; border-radius: 6px; margin: 5px 0; font-size: 12px; border: 1px solid var(--tip-cyan-border, rgba(0, 255, 255, 0.3)); color: var(--tip-cyan-text, #00ffff);">
                💡 <b>推荐组合</b>（最少需要 3 个项目：2简介+1深度）:<br/>
                • <b>标准版</b>: 2简介 + 1深度 ≈ 3000字<br/>
                • <b>丰富版</b>: 3简介 + 1深度 ≈ 3500字<br/>
                • <b>深度版</b>: 2简介 + 2深度 ≈ 4500字<br/>
                • <b>长文版</b>: 3简介 + 2深度 ≈ 6000字
                </div>
                """)

                github_dry_run = gr.Checkbox(
                    label="🧪 试运行模式（不推送）",
                    value=True
                )
                github_run_btn = gr.Button("🔥 开始生成", variant="primary", size="lg")

            with gr.Column(scale=2):
                gr.Markdown("### 📋 执行日志")
                github_log_output = gr.Markdown()

        gr.Markdown("### 📝 产出预览")
        github_article_output = gr.Textbox(label="生成的文章", lines=15)

        github_run_btn.click(
            fn=lambda k, s, b, d, w, r: asyncio.run(run_github_template(k, s, b, d, w, r)),
            inputs=[github_keyword_input, github_min_stars_input, github_brief_count, github_deep_count, github_min_words, github_dry_run],
            outputs=[github_log_output, github_article_output]
        )
