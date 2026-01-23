"""
Hunter AI 内容工厂 - Gradio Web UI

功能：
- 提供可视化的 Web 操作界面
- 上下分离布局：功能区 + 介绍区
- 浅粉色卡通风格，简洁大方

使用方法：
    uv run hunter web          # 启动 Web UI
    uv run python -m src.gradio_app  # 直接运行

GitHub: https://github.com/Pangu-Immortal/hunter-ai-content-factory
Author: Pangu-Immortal
"""

import asyncio
import gradio as gr
from pathlib import Path
from datetime import datetime
from rich.console import Console

# 终端输出
console = Console()

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent

# ═══════════════════════════════════════════════════════════════════════════════
# 自定义 CSS 样式 - 浅粉色卡通风格，上下分离布局
# ═══════════════════════════════════════════════════════════════════════════════

CUSTOM_CSS = """
/* 全局背景 - 浅粉色渐变 */
.gradio-container {
    background: linear-gradient(135deg, #fff0f5 0%, #ffe4ec 50%, #ffd6e0 100%) !important;
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans SC", "Helvetica Neue", Arial, sans-serif !important;
    font-size: 15px !important;
    line-height: 1.6 !important;
    max-width: 1400px !important;
    margin: 0 auto !important;
}

/* 移除图片组件的边框和容器样式 */
.gradio-image {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
}

.gradio-image > div {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    padding: 0 !important;
}

.gradio-image img {
    border-radius: 12px !important;
    border: none !important;
}

/* 隐藏图片组件的下载按钮等工具栏 */
.gradio-image .icon-buttons {
    display: none !important;
}

/* 标题区域 - 无边框融入背景 */
.header-section {
    text-align: center;
    padding: 30px 20px;
    background: transparent;
    margin-bottom: 20px;
}

/* 功能卡片区域 */
.function-card {
    background: rgba(255,255,255,0.95) !important;
    border-radius: 16px !important;
    border: 2px solid #ffb6c1 !important;
    padding: 20px !important;
    box-shadow: 0 4px 15px rgba(255,182,193,0.2) !important;
    transition: all 0.3s ease !important;
}

.function-card:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(255,182,193,0.3) !important;
}

/* Tab 按钮样式 */
.tab-nav button {
    background: linear-gradient(145deg, #fff, #ffe4ec) !important;
    border: 2px solid #ffb6c1 !important;
    border-radius: 12px !important;
    margin: 3px !important;
    padding: 10px 20px !important;
    font-weight: 600 !important;
    color: #d63384 !important;
    transition: all 0.3s ease !important;
}

.tab-nav button:hover {
    background: linear-gradient(145deg, #ff69b4, #ff85a2) !important;
    color: white !important;
}

.tab-nav button.selected {
    background: linear-gradient(145deg, #ff1493, #ff69b4) !important;
    color: white !important;
    box-shadow: 0 4px 15px rgba(255,20,147,0.4) !important;
}

/* 主按钮样式 */
.primary {
    background: linear-gradient(145deg, #ff69b4, #ff1493) !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: bold !important;
    box-shadow: 0 4px 15px rgba(255,20,147,0.3) !important;
    transition: all 0.3s ease !important;
    padding: 12px 30px !important;
}

.primary:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(255,20,147,0.4) !important;
}

/* 分隔线 */
.section-divider {
    height: 3px;
    background: linear-gradient(90deg, transparent, #ffb6c1, transparent);
    margin: 30px 0;
    border-radius: 3px;
}

/* 介绍卡片样式 */
.intro-card {
    background: white !important;
    border-radius: 16px !important;
    overflow: hidden !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08) !important;
    transition: all 0.3s ease !important;
}

.intro-card:hover {
    transform: translateY(-4px) !important;
    box-shadow: 0 8px 30px rgba(255,105,180,0.2) !important;
}

.intro-card img {
    width: 100%;
    height: 200px;
    object-fit: cover;
}

/* 输入框样式 */
textarea, input[type="text"] {
    border: 2px solid #ffb6c1 !important;
    border-radius: 12px !important;
    background: rgba(255,255,255,0.95) !important;
    padding: 12px !important;
}

textarea:focus, input[type="text"]:focus {
    border-color: #ff69b4 !important;
    box-shadow: 0 0 10px rgba(255,105,180,0.2) !important;
}

/* 代码和等宽字体 */
input, textarea, code, pre {
    font-family: "SF Mono", "Monaco", "Consolas", monospace !important;
}

/* 页脚样式 */
.footer {
    text-align: center;
    padding: 20px;
    margin-top: 30px;
    border-top: 2px solid #ffb6c1;
    color: #999;
}
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 6-Skill 数据定义
# ═══════════════════════════════════════════════════════════════════════════════

SKILLS_INFO = [
    {
        "id": "topic",
        "emoji": "🎯",
        "name": "Topic 选题",
        "subtitle": "找到值得写的爆款选题",
        "image": "hunter_intro_02.png",
        "description": "从海量信息中找到值得写的爆款选题，分析热点趋势，确定最佳切入角度。",
        "outputs": ["选定主题", "切入角度", "目标读者", "标题候选"],
        "color": "#ff6b6b"
    },
    {
        "id": "research",
        "emoji": "🔬",
        "name": "Research 研究",
        "subtitle": "收集高质量素材",
        "image": "hunter_intro_04.png",
        "description": "根据选题搜索相关资料，提取核心观点和数据，验证信息可靠性。",
        "outputs": ["核心洞察", "事实数据", "来源列表", "详细笔记"],
        "color": "#4ecdc4"
    },
    {
        "id": "structure",
        "emoji": "🏗️",
        "name": "Structure 结构",
        "subtitle": "设计节奏明快的大纲",
        "image": "hunter_intro_06.png",
        "description": "设计文章骨架和阅读节奏，规划引人入胜的开篇钩子和有力的结尾。",
        "outputs": ["开篇钩子", "章节大纲", "结尾设计", "预估字数"],
        "color": "#45b7d1"
    },
    {
        "id": "write",
        "emoji": "✍️",
        "name": "Write 写作",
        "subtitle": "撰写有人味的初稿",
        "image": "hunter_intro_08.png",
        "description": "根据大纲撰写完整文章，融入研究素材，自动过滤 AI 痕迹词。",
        "outputs": ["完整初稿", "实际字数", "可读性评分"],
        "color": "#96ceb4"
    },
    {
        "id": "package",
        "emoji": "🎁",
        "name": "Package 封装",
        "subtitle": "打造高点击率包装",
        "image": "hunter_intro_10.png",
        "description": "为文章打造吸睛外包装，生成标题选项、精炼摘要、封面图 Prompt。",
        "outputs": ["最终标题", "备选标题", "文章摘要", "封面提示词"],
        "color": "#ffeaa7"
    },
    {
        "id": "publish",
        "emoji": "🚀",
        "name": "Publish 发布",
        "subtitle": "一键推送到微信",
        "image": "hunter_intro_12.png",
        "description": "最终违禁词检查，格式化推送内容，通过 PushPlus 一键推送到微信。",
        "outputs": ["推送状态", "推送时间", "消息 ID"],
        "color": "#dfe6e9"
    }
]

# ═══════════════════════════════════════════════════════════════════════════════
# 功能实现函数
# ═══════════════════════════════════════════════════════════════════════════════

async def run_full_workflow(niche: str, trends: str, progress=gr.Progress()):
    """运行完整工作流"""
    try:
        from src.factory.executor import WorkflowExecutor

        trend_list = [t.strip() for t in trends.split(',') if t.strip()]
        executor = WorkflowExecutor()

        skill_progress = {
            "topic": "1/6", "research": "2/6", "structure": "3/6",
            "write": "4/6", "package": "5/6", "publish": "6/6"
        }

        current_status = "正在初始化..."

        def on_skill_complete(skill_name, context):
            nonlocal current_status
            current_status = f"✅ {skill_name} 完成 ({skill_progress.get(skill_name, '')})"

        context = await executor.run(
            niche=niche or "AI技术",
            trends=trend_list,
            on_skill_complete=on_skill_complete
        )

        result = f"""
## ✅ 工作流执行完成！

### 📌 选题信息
- **主题**: {context.topic.selected_topic}
- **角度**: {context.topic.angle}

### 📝 文章信息
- **标题**: {context.package.title}
- **字数**: {context.write.actual_word_count}

### 🚀 发布状态
- **状态**: {context.publish.push_status}
        """

        return result, context.write.draft

    except ImportError as e:
        return f"""## ❌ 模块导入失败

**错误**: {str(e)}

### 💡 解决方案
1. 确保已安装所有依赖：`uv sync`
2. 检查 `src/factory/executor.py` 是否存在
""", ""

    except FileNotFoundError as e:
        return f"""## ❌ 文件未找到

**错误**: {str(e)}

### 💡 解决方案
1. 检查 `config.yaml` 配置文件是否存在
2. 运行 `cp config.example.yaml config.yaml` 创建配置
""", ""

    except Exception as e:
        error_msg = str(e)
        # 识别常见错误并给出友好提示
        if "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower():
            return f"""## ❌ API 密钥错误

**错误**: {error_msg}

### 💡 解决方案
1. 检查 `config.yaml` 中的 `gemini.api_key` 是否正确
2. 确认 API Key 未过期
3. 如使用第三方服务，检查 `base_url` 是否正确
""", ""
        elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            return f"""## ❌ 网络连接失败

**错误**: {error_msg}

### 💡 解决方案
1. 检查网络连接是否正常
2. 如使用官方 API，可能需要代理
3. 尝试使用第三方聚合服务（如 packyapi）
""", ""
        else:
            return f"""## ❌ 执行失败

**错误**: {error_msg}

### 💡 常见问题排查
1. 检查配置文件 `config.yaml` 是否完整
2. 确认 API Key 已正确配置
3. 查看终端输出获取详细日志
""", ""


def run_content_check(content: str):
    """检查内容违禁词"""
    if not content or not content.strip():
        return "⚠️ **请输入内容** | 粘贴你的文章内容后再检查", ""

    try:
        from src.utils.content_filter import ContentFilter
        from src.config import settings

        filter_instance = ContentFilter(
            banned_words=settings.content.banned_words,
            replacements=settings.content.ai_word_replacements,
        )

        result = filter_instance.check(content)

        if result.passed:
            return "✅ **检查通过！** 未发现违禁词。", content
        else:
            return f"⚠️ **发现违禁词**: {', '.join(result.found_words)}\n\n请修改后再发布。", content

    except ImportError:
        return "❌ **模块未找到** | 请确保已运行 `uv sync` 安装依赖", content
    except Exception as e:
        return f"❌ **检查失败**: {str(e)}\n\n💡 请检查配置文件是否正确", content


def run_content_clean(content: str):
    """清理内容中的 AI 痕迹词"""
    if not content or not content.strip():
        return "⚠️ **请输入内容** | 粘贴你的文章内容后再清理", ""

    try:
        from src.utils.content_filter import ContentFilter
        from src.config import settings

        filter_instance = ContentFilter(
            banned_words=settings.content.banned_words,
            replacements=settings.content.ai_word_replacements,
        )

        cleaned, result = filter_instance.check_and_clean(content)

        report = f"✅ **清理完成** | 替换了 {len(result.replaced_words)} 处 AI 痕迹词"
        return report, cleaned

    except ImportError:
        return "❌ **模块未找到** | 请确保已运行 `uv sync` 安装依赖", content
    except Exception as e:
        return f"❌ **清理失败**: {str(e)}\n\n💡 请检查配置文件是否正确", content


def get_config_info():
    """获取配置信息"""
    try:
        from src.config import get_settings, get_config_status

        get_settings.cache_clear()
        settings = get_settings()
        status = get_config_status()

        gemini_status = '✅' if status['gemini']['api_key_configured'] else '❌'
        github_status = '✅' if status['github']['token_configured'] else '⚪'
        push_status = '✅' if status['pushplus']['token_configured'] else '⚪'

        return f"""
| 配置项 | 状态 | 值 |
|--------|:----:|-----|
| Gemini API | {gemini_status} | {settings.gemini.model} |
| GitHub Token | {github_status} | Stars ≥ {settings.github.min_stars} |
| PushPlus | {push_status} | {'启用' if settings.push.enabled else '禁用'} |
| 公众号 | ✅ | {settings.account.name} ({settings.account.niche}) |
        """

    except FileNotFoundError:
        return """
⚠️ **配置文件未找到**

请先创建配置文件：
```bash
cp config.example.yaml config.yaml
```
        """
    except Exception as e:
        return f"""
❌ **获取配置失败**: {str(e)}

💡 请检查 `config.yaml` 文件格式是否正确
        """


def load_current_config():
    """加载当前配置值"""
    try:
        from src.config import get_settings
        get_settings.cache_clear()
        settings = get_settings()

        return {
            'gemini_provider': settings.gemini.provider or "official",
            'gemini_base_url': settings.gemini.base_url or "",
            'gemini_api_key': settings.gemini.api_key or "",
            'gemini_model': settings.gemini.model or "gemini-2.0-flash",
            'github_token': settings.github.token or "",
            'github_min_stars': settings.github.min_stars,
            'push_token': settings.push.token or "",
            'push_enabled': settings.push.enabled,
            'account_name': settings.account.name or "AI技术前沿",
            'account_niche': settings.account.niche or "AI技术",
            'account_tone': settings.account.tone or "专业且引人入胜",
            'min_length': settings.account.min_length,
            'max_length': settings.account.max_length,
        }
    except Exception:
        return {
            'gemini_provider': "official", 'gemini_base_url': "", 'gemini_api_key': "",
            'gemini_model': "gemini-2.0-flash", 'github_token': "", 'github_min_stars': 200,
            'push_token': "", 'push_enabled': True, 'account_name': "AI技术前沿",
            'account_niche': "AI技术", 'account_tone': "专业且引人入胜",
            'min_length': 1500, 'max_length': 2500,
        }


def save_config(
    gemini_provider, gemini_base_url, gemini_api_key, gemini_model,
    github_token, github_min_stars, push_token, push_enabled,
    account_name, account_niche, account_tone, min_length, max_length
):
    """保存配置"""
    try:
        import yaml

        config_path = ROOT_DIR / "config.yaml"
        config_example = ROOT_DIR / "config.example.yaml"

        if not config_path.exists() and config_example.exists():
            import shutil
            shutil.copy(config_example, config_path)

        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}

        # 更新配置
        config.setdefault('gemini', {})
        config['gemini']['provider'] = gemini_provider
        config['gemini']['base_url'] = gemini_base_url
        config['gemini']['api_key'] = gemini_api_key
        config['gemini']['model'] = gemini_model

        config.setdefault('github', {})
        config['github']['token'] = github_token
        config['github']['min_stars'] = int(github_min_stars)

        config.setdefault('pushplus', {})
        config['pushplus']['token'] = push_token
        config['pushplus']['enabled'] = push_enabled

        config.setdefault('account', {})
        config['account']['name'] = account_name
        config['account']['niche'] = account_niche
        config['account']['tone'] = account_tone
        config['account']['min_length'] = int(min_length)
        config['account']['max_length'] = int(max_length)

        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        from src.config import get_settings
        get_settings.cache_clear()

        return "✅ **配置已保存！** 部分设置需重启生效。"

    except Exception as e:
        return f"❌ 保存失败: {str(e)}"


def get_image_path(filename: str) -> str:
    """获取图片路径"""
    img_path = ROOT_DIR / "docs" / "images" / filename
    if img_path.exists():
        return str(img_path)
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Gradio 界面构建 - 上下分离布局
# ═══════════════════════════════════════════════════════════════════════════════

def create_app():
    """创建 Gradio 应用"""

    with gr.Blocks(title="Hunter AI 内容工厂") as app:

        # ═══════════════════════════════════════════════════════════════════
        # 顶部标题 - 无边框融入背景
        # ═══════════════════════════════════════════════════════════════════
        gr.HTML("""
        <div style="text-align: center; padding: 25px 20px;">
            <h1 style="font-size: 2.5em; margin: 0; color: #e91e63; text-shadow: 2px 2px 4px rgba(233,30,99,0.2);">
                🦅 Hunter AI 内容工厂
            </h1>
            <p style="font-size: 1.1em; color: #666; margin: 10px 0 0 0;">
                一键生成高质量公众号文章的 AI 工作流
            </p>
        </div>
        """)

        # ═══════════════════════════════════════════════════════════════════
        # 上部功能区 - 三个核心功能 Tab
        # ═══════════════════════════════════════════════════════════════════
        with gr.Tabs() as top_tabs:

            # ─────────────────────────────────────────────────────────────────
            # Tab: 一键运行
            # ─────────────────────────────────────────────────────────────────
            with gr.Tab("🚀 一键运行", id="run"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 参数设置")
                        niche_input = gr.Textbox(
                            label="📌 细分领域",
                            placeholder="AI技术、Python开发...",
                            value="AI技术"
                        )
                        trends_input = gr.Textbox(
                            label="🔥 热点趋势",
                            placeholder="用逗号分隔多个关键词",
                            value="Claude 4, MCP协议, Agent编排"
                        )
                        run_btn = gr.Button("🚀 开始执行", variant="primary", size="lg")

                    with gr.Column(scale=2):
                        gr.Markdown("### 执行结果")
                        status_output = gr.Markdown()
                        article_output = gr.Textbox(label="📝 生成的文章", lines=12)

                run_btn.click(
                    fn=lambda n, t: asyncio.run(run_full_workflow(n, t)),
                    inputs=[niche_input, trends_input],
                    outputs=[status_output, article_output]
                )

            # ─────────────────────────────────────────────────────────────────
            # Tab: 内容审核
            # ─────────────────────────────────────────────────────────────────
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

            # ─────────────────────────────────────────────────────────────────
            # Tab: 设置
            # ─────────────────────────────────────────────────────────────────
            with gr.Tab("⚙️ 设置", id="settings"):
                current_config = load_current_config()

                with gr.Row():
                    # 左侧：配置表单
                    with gr.Column(scale=2):
                        with gr.Accordion("🤖 Gemini AI 配置", open=True):
                            gemini_provider = gr.Radio(
                                label="API 提供商",
                                choices=["official", "openai_compatible"],
                                value=current_config['gemini_provider'],
                                info="official=官方 | openai_compatible=第三方聚合"
                            )
                            gemini_base_url = gr.Textbox(
                                label="API 地址 (第三方需要)",
                                placeholder="https://www.packyapi.com/v1",
                                value=current_config['gemini_base_url']
                            )
                            gemini_api_key = gr.Textbox(
                                label="API Key",
                                value=current_config['gemini_api_key'],
                                type="password"
                            )
                            gemini_model = gr.Dropdown(
                                label="模型",
                                choices=[
                                    "gemini-2.0-flash", "gemini-1.5-pro",
                                    "gemini-3-pro-preview", "gemini-3-flash-preview",
                                    "gemini-2.5-pro", "gemini-2.5-flash",
                                ],
                                value=current_config['gemini_model'],
                                allow_custom_value=True
                            )

                        with gr.Accordion("🐙 GitHub & 📮 PushPlus", open=False):
                            github_token = gr.Textbox(
                                label="GitHub Token",
                                value=current_config['github_token'],
                                type="password"
                            )
                            github_min_stars = gr.Slider(
                                label="最小 Stars",
                                minimum=50, maximum=2000,
                                value=current_config['github_min_stars'],
                                step=50
                            )
                            push_token = gr.Textbox(
                                label="PushPlus Token",
                                value=current_config['push_token'],
                                type="password"
                            )
                            push_enabled = gr.Checkbox(
                                label="启用推送",
                                value=current_config['push_enabled']
                            )

                        with gr.Accordion("📝 公众号设置", open=False):
                            account_name = gr.Textbox(label="名称", value=current_config['account_name'])
                            account_niche = gr.Textbox(label="领域", value=current_config['account_niche'])
                            account_tone = gr.Textbox(label="风格", value=current_config['account_tone'])
                            with gr.Row():
                                min_length = gr.Number(label="最小字数", value=current_config['min_length'])
                                max_length = gr.Number(label="最大字数", value=current_config['max_length'])

                    # 右侧：状态显示
                    with gr.Column(scale=1):
                        gr.Markdown("### 当前配置状态")
                        config_status = gr.Markdown(value=get_config_info())

                        save_btn = gr.Button("💾 保存配置", variant="primary", size="lg")
                        save_output = gr.Markdown()

                        refresh_btn = gr.Button("🔄 刷新状态", variant="secondary")

                save_btn.click(
                    fn=save_config,
                    inputs=[
                        gemini_provider, gemini_base_url, gemini_api_key, gemini_model,
                        github_token, github_min_stars, push_token, push_enabled,
                        account_name, account_niche, account_tone, min_length, max_length
                    ],
                    outputs=[save_output]
                )
                refresh_btn.click(fn=get_config_info, outputs=[config_status])

        # ═══════════════════════════════════════════════════════════════════
        # 分隔线
        # ═══════════════════════════════════════════════════════════════════
        gr.HTML("""
        <div style="height: 3px; background: linear-gradient(90deg, transparent, #ffb6c1, transparent); margin: 30px 0; border-radius: 3px;"></div>
        """)

        # ═══════════════════════════════════════════════════════════════════
        # 下部介绍区 - 首页 + 6 个 Skill 介绍
        # ═══════════════════════════════════════════════════════════════════
        gr.Markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <h2 style="color: #e91e63;">📚 6-Skill 工作流介绍</h2>
            <p style="color: #666;">像流水线一样高效协作，从选题到发布一气呵成</p>
        </div>
        """)

        with gr.Tabs() as bottom_tabs:

            # ─────────────────────────────────────────────────────────────────
            # Tab: 首页介绍
            # ─────────────────────────────────────────────────────────────────
            with gr.Tab("🏠 首页", id="home"):
                with gr.Row():
                    with gr.Column(scale=1):
                        # 显示主图 - 无边框
                        main_img = get_image_path("hunter_intro_03.png")
                        if main_img:
                            gr.Image(main_img, label=None, show_label=False, height=300,
                                    container=False)
                    with gr.Column(scale=2):
                        gr.Markdown("""
### 🦅 Hunter AI 内容工厂

基于 **6-Skill 架构** 的智能内容生产系统。

#### 核心特点
| 特性 | 说明 |
|------|------|
| 🧩 **模块化** | 每个 Skill 独立运行，可单独调试 |
| 📍 **可追溯** | 每一步都有明确的输入输出 |
| 🔄 **可恢复** | 支持断点续作 |
| 🚫 **去 AI 化** | 内置违禁词检查，自动清理 AI 痕迹 |

#### 工作流程
```
选题 → 研究 → 结构 → 写作 → 封装 → 发布
```
                        """)

            # ─────────────────────────────────────────────────────────────────
            # 6 个 Skill Tab
            # ─────────────────────────────────────────────────────────────────
            for skill in SKILLS_INFO:
                with gr.Tab(f"{skill['emoji']} {skill['name']}", id=skill['id']):
                    with gr.Row():
                        with gr.Column(scale=1):
                            img_path = get_image_path(skill['image'])
                            if img_path:
                                gr.Image(img_path, label=None, show_label=False, height=250,
                                        container=False)
                            else:
                                gr.HTML(f"""
                                <div style="height: 250px; display: flex; align-items: center; justify-content: center;
                                    background: linear-gradient(135deg, {skill['color']}22, {skill['color']}44);
                                    border-radius: 16px; font-size: 5em;">
                                    {skill['emoji']}
                                </div>
                                """)

                        with gr.Column(scale=2):
                            gr.Markdown(f"""
### {skill['emoji']} {skill['name']}

**{skill['subtitle']}**

{skill['description']}

#### 输出内容
| 输出项 | 说明 |
|--------|------|
""" + "\n".join([f"| {out} | 由 AI 自动生成 |" for out in skill['outputs']]))

        # ═══════════════════════════════════════════════════════════════════
        # 页脚
        # ═══════════════════════════════════════════════════════════════════
        gr.HTML("""
        <div style="text-align: center; padding: 20px; margin-top: 30px; border-top: 2px solid #ffb6c1;">
            <p style="color: #999; margin: 0;">Made with 💖 by Pangu-Immortal</p>
            <p style="color: #ccc; font-size: 0.9em; margin: 5px 0 0 0;">
                Hunter AI 内容工厂 v3.0 |
                <a href="https://github.com/Pangu-Immortal/hunter-ai-content-factory" style="color: #ff69b4;">GitHub</a>
            </p>
        </div>
        """)

    return app


def main():
    """启动 Gradio 应用"""
    console.print("[bold magenta]🦅 启动 Hunter AI Web UI...[/bold magenta]\n")

    app = create_app()

    console.print("[cyan]本地访问: http://127.0.0.1:7860[/cyan]")
    console.print("[cyan]外链分享: 启动后显示公网链接[/cyan]\n")

    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=True,
        show_error=True,
        inbrowser=True,
        css=CUSTOM_CSS,
        theme=gr.themes.Soft(primary_hue="pink", secondary_hue="rose", neutral_hue="slate"),
    )


if __name__ == "__main__":
    main()
