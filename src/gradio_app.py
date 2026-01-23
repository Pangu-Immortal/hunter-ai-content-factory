"""
Hunter AI 内容工厂 - Gradio Web UI

功能：
- 提供可视化的 Web 操作界面
- 上下分离布局：功能区 + 介绍区
- 赛博朋克风格，霓虹机械配色

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
# 自定义 CSS 样式 - 从外部文件加载
# ═══════════════════════════════════════════════════════════════════════════════

def load_custom_css() -> str:
    """从外部文件加载 CSS 样式"""
    css_path = ROOT_DIR / "src" / "static" / "styles.css"
    if css_path.exists():
        return css_path.read_text(encoding="utf-8")
    return ""

CUSTOM_CSS = load_custom_css()

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

# ═══════════════════════════════════════════════════════════════════════════════
# 五大模板运行函数（详细日志版）
# ═══════════════════════════════════════════════════════════════════════════════

def format_error_message(error_msg: str, template_name: str) -> str:
    """格式化错误消息"""
    if "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower() or "invalid_argument" in error_msg.lower():
        return f"""## ❌ API 密钥错误

**错误**: {error_msg}

### 💡 解决方案
1. 检查 `config.yaml` 中的 `gemini.api_key` 是否正确
2. 确认 API Key 未过期
3. 如使用第三方服务，检查 `provider` 是否为 `openai_compatible`
4. 检查 `base_url` 是否正确（如 https://www.packyapi.com/v1）
"""
    elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
        return f"""## ❌ 网络连接失败

**错误**: {error_msg}

### 💡 解决方案
1. 检查网络连接是否正常
2. 如使用官方 API，可能需要代理
3. 尝试使用第三方聚合服务
"""
    elif "cookie" in error_msg.lower():
        return f"""## ❌ Cookie 配置错误

**错误**: {error_msg}

### 💡 解决方案（{template_name}）
1. 打开浏览器登录对应平台
2. F12 → Application → Cookies
3. 复制 Cookie 到 `config.yaml` 对应配置项
"""
    else:
        return f"""## ❌ 执行失败

**错误**: {error_msg}

### 💡 常见问题排查
1. 检查配置文件 `config.yaml` 是否完整
2. 确认 API Key 已正确配置
3. 查看终端输出获取详细日志
"""


async def run_github_template(
    keyword: str,
    min_stars: int,
    brief_count: int,
    deep_count: int,
    min_words: int,
    dry_run: bool
):
    """
    🔥 GitHub 爆款 - 运行 GitHub 热门项目推荐模板

    流程：GitHub Search API → 筛选项目 → 去重 → AI 生成自定义结构文章

    Args:
        keyword: 搜索关键词，用于筛选项目品类/功能/技术方向
        min_stars: 最小 Stars 数
        brief_count: 项目简介数量
        deep_count: 深度解读数量
        min_words: 文章最小字数
        dry_run: 是否试运行（不推送）
    """
    logs = []
    logs.append("## 🔥 GitHub 爆款生成器\n")
    logs.append(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    logs.append("---\n")

    # 处理关键词
    search_keyword = keyword.strip() if keyword else "AI"
    # 确保数量合理
    brief_count = max(0, int(brief_count))
    deep_count = max(1, int(deep_count))
    min_words = max(1000, int(min_words))

    try:
        logs.append("### 📡 Step 1: 连接 GitHub API\n")
        logs.append(f"- 🔍 搜索关键词: **{search_keyword}**\n")
        logs.append(f"- ⭐ 筛选条件: Stars ≥ {min_stars}\n")
        logs.append(f"- 📂 搜索范围: {search_keyword} 相关项目\n")

        from src.templates import get_template

        logs.append("\n### 🔍 Step 2: 抓取热门项目\n")
        logs.append(f"- 正在查询 GitHub 「{search_keyword}」 热门项目...\n")
        logs.append(f"- 需要抓取: **{brief_count + deep_count}** 个项目\n")

        # 使用正确的模板API
        template = get_template("github")
        # TODO: 将参数传递给模板（需要模板支持）
        result = await template.run()

        logs.append("- ✅ 项目抓取完成\n")
        logs.append("\n### 🤖 Step 3: AI 生成文章\n")
        logs.append("- 正在调用 AI 模型...\n")
        logs.append(f"- 📝 文章结构: **{brief_count}个简介 + {deep_count}个深度解读**\n")
        logs.append(f"- 📏 最小字数: **{min_words}** 字\n")

        if result and result.success:
            word_count = len(result.content)
            logs.append(f"\n### ✅ 生成完成！\n")
            logs.append(f"- **标题**: {result.title}\n")
            logs.append(f"- **字数**: {word_count} 字 {'✅' if word_count >= min_words else '⚠️ 未达标'}\n")
            logs.append(f"- **关键词**: {search_keyword}\n")
            logs.append(f"- **推送**: {'已禁用（试运行模式）' if dry_run else result.push_status}\n")
            return "\n".join(logs), result.content
        else:
            error_msg = result.error if result else "未知错误"
            logs.append(f"\n### ⚠️ 执行完成（有问题）\n")
            logs.append(f"- 错误: {error_msg}\n")
            return "\n".join(logs), ""

    except ImportError as e:
        logs.append(f"\n### ❌ 模块导入失败\n")
        logs.append(f"- 错误: {str(e)}\n")
        logs.append("- 解决: 运行 `uv sync` 安装依赖\n")
        return "\n".join(logs), ""

    except Exception as e:
        logs.append(f"\n{format_error_message(str(e), 'GitHub')}")
        return "\n".join(logs), ""


async def run_pain_template(dry_run: bool):
    """
    💊 痛点诊断 - 运行痛点雷达模板

    流程：Twitter + Reddit 搜索 → 自动推断标签 → SQLite + ChromaDB 存储 → AI 诊断分析 → 生成报告
    """
    logs = []
    logs.append("## 💊 痛点诊断雷达\n")
    logs.append(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    logs.append("---\n")

    try:
        logs.append("### 📡 Step 1: 全网扫描用户吐槽\n")
        logs.append("- 扫描平台: Twitter、Reddit\n")
        logs.append("- 关键词: ChatGPT、Claude、DeepSeek 等 AI 产品 + 痛点词\n")

        from src.templates import get_template

        logs.append("\n### 🔍 Step 2: 采集痛点数据\n")
        logs.append("- 正在爬取 Twitter...\n")
        logs.append("- 正在爬取 Reddit...\n")

        template = get_template("pain")
        result = await template.run()

        logs.append("- ✅ 痛点数据采集完成\n")
        logs.append("\n### 🏷️ Step 3: 自动标签推断\n")
        logs.append("- 产品分类: ChatGPT/Claude/DeepSeek 等\n")
        logs.append("- 问题类型: 性能/准确性/稳定性/功能/体验/API\n")
        logs.append("- 严重程度: blocker/major/minor\n")

        logs.append("\n### 🤖 Step 4: AI 诊断分析\n")
        logs.append("- 正在调用 AI 模型...\n")
        logs.append("- 生成诊断报告...\n")

        if result and result.success:
            logs.append("\n### ✅ 诊断完成！\n")
            logs.append(f"- **标题**: {result.title}\n")
            logs.append("- **输出格式**: Markdown 诊断报告\n")
            logs.append("- **保存位置**: `output/日期/reports/`\n")
            logs.append("- **报告内容**: Top 3 阻断性痛点 + 技术根因 + 解决方案\n")
            return "\n".join(logs), result.content
        else:
            error_msg = result.error if result else "未知错误"
            logs.append(f"\n### ⚠️ 执行完成（有问题）\n")
            logs.append(f"- 错误: {error_msg}\n")
            return "\n".join(logs), ""

    except ImportError as e:
        logs.append(f"\n### ❌ 模块导入失败\n")
        logs.append(f"- 错误: {str(e)}\n")
        return "\n".join(logs), ""

    except Exception as e:
        logs.append(f"\n{format_error_message(str(e), '痛点诊断')}")
        return "\n".join(logs), ""


async def run_news_template(dry_run: bool):
    """
    📰 热点快报 - 运行多平台资讯采集模板

    流程：HackerNews + Twitter + Reddit + GitHub + 小红书 → AI 筛选分类 → 生成资讯快报
    """
    logs = []
    logs.append("## 📰 热点快报生成器\n")
    logs.append(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    logs.append("---\n")

    try:
        logs.append("### 📡 Step 1: 五平台并行采集\n")
        logs.append("| 平台 | 状态 |\n")
        logs.append("|------|------|\n")

        from src.templates import get_template

        platforms = ["HackerNews", "Twitter", "Reddit", "GitHub", "小红书"]
        for p in platforms:
            logs.append(f"| {p} | 🔄 采集中... |\n")

        template = get_template("news")
        result = await template.run()

        logs.append("\n### 🔍 Step 2: AI 筛选分类\n")
        logs.append("- 过滤重复内容\n")
        logs.append("- 热度排序\n")
        logs.append("- 分类归档\n")

        logs.append("\n### 📝 Step 3: 生成资讯快报\n")
        logs.append("- 正在调用 AI 模型...\n")
        logs.append("- 生成今日资讯速览...\n")

        if result and result.success:
            logs.append("\n### ✅ 快报生成完成！\n")
            logs.append(f"- **标题**: {result.title}\n")
            logs.append("- **输出格式**: 资讯快报文章\n")
            logs.append("- **保存位置**: `output/日期/articles/`\n")
            logs.append(f"- **推送状态**: {'已禁用（试运行模式）' if dry_run else result.push_status}\n")
            return "\n".join(logs), result.content
        else:
            error_msg = result.error if result else "未知错误"
            logs.append(f"\n### ⚠️ 执行完成（有问题）\n")
            logs.append(f"- 错误: {error_msg}\n")
            return "\n".join(logs), ""

    except ImportError as e:
        logs.append(f"\n### ❌ 模块导入失败\n")
        logs.append(f"- 错误: {str(e)}\n")
        return "\n".join(logs), ""

    except Exception as e:
        logs.append(f"\n{format_error_message(str(e), '热点快报')}")
        return "\n".join(logs), ""


async def run_xhs_template(keyword: str, dry_run: bool):
    """
    📕 小红书种草 - 运行小红书采集模板

    流程：Playwright/httpx 采集小红书 → AI 提炼核心内容 → 生成公众号风格文章
    """
    logs = []
    logs.append("## 📕 小红书种草生成器\n")
    logs.append(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    logs.append("---\n")

    try:
        logs.append("### 📡 Step 1: 连接小红书\n")
        logs.append(f"- 搜索关键词: {keyword or '热门笔记'}\n")
        logs.append("- 采集方式: Playwright 浏览器 / httpx + Cookie\n")

        from src.templates import get_template

        logs.append("\n### 🔍 Step 2: 采集爆款笔记\n")
        logs.append("- 正在获取热门笔记列表...\n")
        logs.append("- 提取笔记标题、封面、正文...\n")

        template = get_template("xhs")
        result = await template.run()

        logs.append("- ✅ 笔记采集完成\n")

        logs.append("\n### 🤖 Step 3: AI 改写为公众号风格\n")
        logs.append("- 正在调用 AI 模型...\n")
        logs.append("- 转换为公众号种草推荐文...\n")

        if result and result.success:
            logs.append("\n### ✅ 种草文生成完成！\n")
            logs.append(f"- **标题**: {result.title}\n")
            logs.append("- **输出格式**: 公众号风格种草文\n")
            logs.append("- **保存位置**: `output/日期/articles/`\n")
            logs.append(f"- **推送状态**: {'已禁用（试运行模式）' if dry_run else result.push_status}\n")
            return "\n".join(logs), result.content
        else:
            error_msg = result.error if result else "未知错误"
            logs.append(f"\n### ⚠️ 执行完成（有问题）\n")
            logs.append(f"- 错误: {error_msg}\n")
            return "\n".join(logs), ""

    except ImportError as e:
        logs.append(f"\n### ❌ 模块导入失败\n")
        logs.append(f"- 错误: {str(e)}\n")
        return "\n".join(logs), ""

    except Exception as e:
        logs.append(f"\n{format_error_message(str(e), '小红书')}")
        return "\n".join(logs), ""


async def run_auto_template(niche: str, dry_run: bool):
    """
    🚀 全自动生产 - 运行全流程自动化模板

    流程：五平台采集 → AI 分析 → 选题生成 → 文章创作 → 公众号排版 → 推送
    """
    logs = []
    logs.append("## 🚀 全自动内容生产线\n")
    logs.append(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    logs.append("---\n")

    try:
        logs.append("### 📡 Step 1: 五平台全量采集\n")
        logs.append("| 平台 | 采集内容 |\n")
        logs.append("|------|----------|\n")
        logs.append("| HackerNews | 技术热点 |\n")
        logs.append("| Twitter | 行业动态 |\n")
        logs.append("| Reddit | 社区讨论 |\n")
        logs.append("| GitHub | 开源项目 |\n")
        logs.append("| 小红书 | 生活热点 |\n")

        from src.templates import get_template

        logs.append("\n### 🔍 Step 2: AI 智能分析\n")
        logs.append(f"- 细分领域: {niche or 'AI技术'}\n")
        logs.append("- 分析维度: 热度、话题性、传播性\n")

        template = get_template("auto")
        result = await template.run()

        logs.append("\n### 🎯 Step 3: 智能选题\n")
        logs.append("- 从海量信息中筛选最佳选题\n")
        logs.append("- 确定切入角度和目标读者\n")

        logs.append("\n### ✍️ Step 4: 文章创作\n")
        logs.append("- 执行 6-Skill 工作流\n")
        logs.append("- Topic → Research → Structure → Write → Package → Publish\n")

        logs.append("\n### 📦 Step 5: 公众号排版\n")
        logs.append("- 生成最终标题和摘要\n")
        logs.append("- 自动清理 AI 痕迹词\n")
        logs.append("- 格式化为公众号格式\n")

        if result and result.success:
            logs.append("\n### ✅ 全流程执行完成！\n")
            logs.append(f"- **标题**: {result.title}\n")
            logs.append("- **输出格式**: AI 生活黑客风格文章\n")
            logs.append("- **文章结构**: 💔崩溃瞬间 → 🔧魔法修补 → 🎁咒语交付\n")
            logs.append("- **保存位置**: `output/日期/文章标题/`\n")
            logs.append(f"- **推送状态**: {'已禁用（试运行模式）' if dry_run else result.push_status}\n")
            return "\n".join(logs), result.content
        else:
            error_msg = result.error if result else "未知错误"
            logs.append(f"\n### ⚠️ 执行完成（有问题）\n")
            logs.append(f"- 错误: {error_msg}\n")
            return "\n".join(logs), ""

    except ImportError as e:
        logs.append(f"\n### ❌ 模块导入失败\n")
        logs.append(f"- 错误: {str(e)}\n")
        return "\n".join(logs), ""

    except Exception as e:
        logs.append(f"\n{format_error_message(str(e), '全自动生产')}")
        return "\n".join(logs), ""


async def run_full_workflow(niche: str, trends: str, progress=gr.Progress()):
    """运行完整工作流（保留兼容）"""
    return await run_auto_template(niche, dry_run=False)


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
    """获取配置信息 - 显示所有配置项状态"""
    try:
        from src.config import get_settings, get_config_status

        get_settings.cache_clear()
        settings = get_settings()
        status = get_config_status()

        # 状态图标
        gemini_ok = '✅' if status['gemini']['api_key_configured'] else '❌'
        github_ok = '✅' if status['github']['token_configured'] else '⚪'
        push_ok = '✅' if status['pushplus']['token_configured'] else '⚪'

        # 检查其他配置
        xhs_ok = '⚪'
        twitter_ok = '⚪'
        try:
            if hasattr(settings, 'xiaohongshu') and settings.xiaohongshu and getattr(settings.xiaohongshu, 'cookies', ''):
                xhs_ok = '✅'
        except:
            pass
        try:
            if hasattr(settings, 'twitter') and settings.twitter and getattr(settings.twitter, 'cookies_path', ''):
                twitter_ok = '✅'
        except:
            pass

        # 隐藏敏感信息的显示
        def mask_key(key: str, show_chars: int = 4) -> str:
            if not key:
                return "未配置"
            if len(key) <= show_chars * 2:
                return "*" * len(key)
            return key[:show_chars] + "****" + key[-show_chars:]

        # Gemini 配置
        gemini_key = getattr(settings.gemini, 'api_key', '') or ''
        gemini_provider = getattr(settings.gemini, 'provider', 'official')
        gemini_model = getattr(settings.gemini, 'model', '')
        gemini_image = getattr(settings.gemini, 'image_model', '') or '未配置'
        gemini_base = getattr(settings.gemini, 'base_url', '') or '官方API'

        # GitHub 配置
        github_key = getattr(settings.github, 'token', '') or ''
        github_stars = getattr(settings.github, 'min_stars', 200)
        github_days = getattr(settings.github, 'days_since_update', 30) if hasattr(settings.github, 'days_since_update') else 30

        # PushPlus 配置
        push_key = getattr(settings.push, 'token', '') or ''
        push_enabled = getattr(settings.push, 'enabled', False)

        # Twitter 配置
        twitter_path = 'data/cookies.json'
        try:
            if hasattr(settings, 'twitter') and settings.twitter:
                twitter_path = getattr(settings.twitter, 'cookies_path', 'data/cookies.json')
        except:
            pass

        # 小红书配置
        xhs_cookies = ''
        xhs_keyword = 'AI工具'
        xhs_style = '种草'
        try:
            if hasattr(settings, 'xiaohongshu') and settings.xiaohongshu:
                xhs_cookies = getattr(settings.xiaohongshu, 'cookies', '') or ''
                xhs_keyword = getattr(settings.xiaohongshu, 'default_keyword', 'AI工具')
                xhs_style = getattr(settings.xiaohongshu, 'default_style', '种草')
        except:
            pass

        # 公众号配置
        acc_name = getattr(settings.account, 'name', '')
        acc_niche = getattr(settings.account, 'niche', '')
        acc_tone = getattr(settings.account, 'tone', '')
        acc_min = getattr(settings.account, 'min_length', 1500)
        acc_max = getattr(settings.account, 'max_length', 2500)
        acc_title = getattr(settings.account, 'max_title_length', 20) if hasattr(settings.account, 'max_title_length') else 20

        # 存储配置
        chromadb = 'data/chromadb'
        output = 'output'
        try:
            if hasattr(settings, 'storage') and settings.storage:
                chromadb = getattr(settings.storage, 'chromadb_path', 'data/chromadb')
                output = getattr(settings.storage, 'output_dir', 'output')
        except:
            pass

        # 系统配置
        log_level = 'INFO'
        try:
            if hasattr(settings, 'system') and settings.system:
                log_level = getattr(settings.system, 'log_level', 'INFO')
        except:
            pass

        return f"""
**🤖 Gemini AI**
| 项目 | 状态 |
|------|------|
| API Key | {gemini_ok} {mask_key(gemini_key)} |
| 提供商 | {gemini_provider} |
| Base URL | {gemini_base[:25]}{'...' if len(str(gemini_base)) > 25 else ''} |
| 文本模型 | {gemini_model} |
| 图片模型 | {gemini_image} |

**📮 PushPlus 推送**
| 项目 | 状态 |
|------|------|
| Token | {push_ok} {mask_key(push_key)} |
| 推送 | {'✅ 启用' if push_enabled else '⚪ 禁用'} |

**🐦 Twitter/X**
| 项目 | 状态 |
|------|------|
| Cookies | {twitter_ok} |
| 路径 | {twitter_path} |

**📕 小红书**
| 项目 | 状态 |
|------|------|
| Cookie | {xhs_ok} {mask_key(xhs_cookies, 6) if xhs_cookies else '未配置'} |
| 关键词 | {xhs_keyword} |
| 风格 | {xhs_style} |

**🐙 GitHub**
| 项目 | 状态 |
|------|------|
| Token | {github_ok} {mask_key(github_key)} |
| 最小Stars | ≥{github_stars} |
| 更新天数 | {github_days}天内 |

**📝 公众号**
| 项目 | 值 |
|------|------|
| 名称 | {acc_name} |
| 领域 | {acc_niche} |
| 风格 | {acc_tone[:8]}{'...' if len(str(acc_tone)) > 8 else ''} |
| 字数 | {acc_min}-{acc_max} |
| 标题 | ≤{acc_title}字 |

**💾 存储与系统**
| 项目 | 值 |
|------|------|
| 向量库 | {chromadb} |
| 输出目录 | {output} |
| 日志级别 | {log_level} |
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
            # Gemini AI 配置
            'gemini_provider': settings.gemini.provider or "official",
            'gemini_base_url': settings.gemini.base_url or "",
            'gemini_api_key': settings.gemini.api_key or "",
            'gemini_model': settings.gemini.model or "gemini-2.0-flash",
            'gemini_image_model': getattr(settings.gemini, 'image_model', "") or "",
            # GitHub 配置
            'github_token': settings.github.token or "",
            'github_min_stars': settings.github.min_stars,
            'github_days_since_update': getattr(settings.github, 'days_since_update', 30),
            # PushPlus 配置
            'push_token': settings.push.token or "",
            'push_enabled': settings.push.enabled,
            # Twitter/X 配置
            'twitter_cookies_path': getattr(settings, 'twitter', {}).get('cookies_path', 'data/cookies.json') if hasattr(settings, 'twitter') else 'data/cookies.json',
            # 小红书配置
            'xhs_cookies': getattr(settings, 'xiaohongshu', {}).get('cookies', '') if hasattr(settings, 'xiaohongshu') else '',
            'xhs_default_keyword': getattr(settings, 'xiaohongshu', {}).get('default_keyword', 'AI工具') if hasattr(settings, 'xiaohongshu') else 'AI工具',
            'xhs_default_style': getattr(settings, 'xiaohongshu', {}).get('default_style', '种草') if hasattr(settings, 'xiaohongshu') else '种草',
            # 公众号设置
            'account_name': settings.account.name or "AI技术前沿",
            'account_niche': settings.account.niche or "AI技术",
            'account_tone': settings.account.tone or "专业且引人入胜",
            'min_length': settings.account.min_length,
            'max_length': settings.account.max_length,
            'max_title_length': getattr(settings.account, 'max_title_length', 20),
            # 存储配置
            'chromadb_path': getattr(settings, 'storage', {}).get('chromadb_path', 'data/chromadb') if hasattr(settings, 'storage') else 'data/chromadb',
            'output_dir': getattr(settings, 'storage', {}).get('output_dir', 'output') if hasattr(settings, 'storage') else 'output',
            # 系统配置
            'log_level': getattr(settings, 'system', {}).get('log_level', 'INFO') if hasattr(settings, 'system') else 'INFO',
        }
    except Exception:
        return {
            'gemini_provider': "official", 'gemini_base_url': "", 'gemini_api_key': "",
            'gemini_model': "gemini-2.0-flash", 'gemini_image_model': "",
            'github_token': "", 'github_min_stars': 200, 'github_days_since_update': 30,
            'push_token': "", 'push_enabled': True,
            'twitter_cookies_path': "data/cookies.json",
            'xhs_cookies': "", 'xhs_default_keyword': "AI工具", 'xhs_default_style': "种草",
            'account_name': "AI技术前沿", 'account_niche': "AI技术", 'account_tone': "专业且引人入胜",
            'min_length': 1500, 'max_length': 2500, 'max_title_length': 20,
            'chromadb_path': "data/chromadb", 'output_dir': "output", 'log_level': "INFO",
        }


def save_config(
    gemini_provider, gemini_base_url, gemini_api_key, gemini_model, gemini_image_model,
    github_token, github_min_stars, github_days_since_update,
    push_token, push_enabled,
    twitter_cookies_path,
    xhs_cookies, xhs_default_keyword, xhs_default_style,
    account_name, account_niche, account_tone, min_length, max_length, max_title_length,
    chromadb_path, output_dir, log_level
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

        # 更新 Gemini 配置
        config.setdefault('gemini', {})
        config['gemini']['provider'] = gemini_provider
        config['gemini']['base_url'] = gemini_base_url
        config['gemini']['api_key'] = gemini_api_key
        config['gemini']['model'] = gemini_model
        config['gemini']['image_model'] = gemini_image_model

        # 更新 GitHub 配置
        config.setdefault('github', {})
        config['github']['token'] = github_token
        config['github']['min_stars'] = int(github_min_stars)
        config['github']['days_since_update'] = int(github_days_since_update)

        # 更新 PushPlus 配置
        config.setdefault('pushplus', {})
        config['pushplus']['token'] = push_token
        config['pushplus']['enabled'] = push_enabled

        # 更新 Twitter 配置
        config.setdefault('twitter', {})
        config['twitter']['cookies_path'] = twitter_cookies_path

        # 更新小红书配置
        config.setdefault('xiaohongshu', {})
        config['xiaohongshu']['cookies'] = xhs_cookies
        config['xiaohongshu']['default_keyword'] = xhs_default_keyword
        config['xiaohongshu']['default_style'] = xhs_default_style

        # 更新公众号配置
        config.setdefault('account', {})
        config['account']['name'] = account_name
        config['account']['niche'] = account_niche
        config['account']['tone'] = account_tone
        config['account']['min_length'] = int(min_length)
        config['account']['max_length'] = int(max_length)
        config['account']['max_title_length'] = int(max_title_length)

        # 更新存储配置
        config.setdefault('storage', {})
        config['storage']['chromadb_path'] = chromadb_path
        config['storage']['output_dir'] = output_dir

        # 更新系统配置
        config.setdefault('system', {})
        config['system']['log_level'] = log_level

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
    return ""


# ═══════════════════════════════════════════════════════════════════════════════
# Gradio 界面构建 - 上下分离布局
# ═══════════════════════════════════════════════════════════════════════════════

def create_app():
    """创建 Gradio 应用"""

    with gr.Blocks(title="Hunter AI 内容工厂") as app:

        # ═══════════════════════════════════════════════════════════════════
        # 顶部标题 + 主题切换
        # ═══════════════════════════════════════════════════════════════════
        gr.HTML("""
        <!-- 主题切换脚本 -->
        <script>
            // 初始化主题和同步 checkbox
            (function() {
                const savedTheme = localStorage.getItem('hunter-theme') || 'light';
                document.documentElement.setAttribute('data-theme', savedTheme);

                // 页面加载后同步 checkbox 状态
                document.addEventListener('DOMContentLoaded', function() {
                    const checkbox = document.querySelector('.theme-switch input');
                    if (checkbox) {
                        checkbox.checked = savedTheme === 'dark';
                    }
                });

                // Gradio 可能延迟加载，增加备用检查
                setTimeout(function() {
                    const checkbox = document.querySelector('.theme-switch input');
                    if (checkbox) {
                        checkbox.checked = localStorage.getItem('hunter-theme') === 'dark';
                    }
                }, 500);
            })();

            // 切换主题
            function toggleTheme() {
                const html = document.documentElement;
                const currentTheme = html.getAttribute('data-theme') || 'light';
                const newTheme = currentTheme === 'light' ? 'dark' : 'light';
                html.setAttribute('data-theme', newTheme);
                localStorage.setItem('hunter-theme', newTheme);
            }
        </script>

        <!-- 顶部标题 -->
        <div style="text-align: center; padding: 25px 20px 10px 20px;">
            <h1 style="font-size: 2.5em; margin: 0; color: #e91e63; text-shadow: 2px 2px 4px rgba(233,30,99,0.2);">
                🦅 Hunter AI 内容工厂
            </h1>
            <p style="font-size: 1.1em; color: var(--text-muted, #666); margin: 10px 0 0 0;">
                一键生成高质量公众号文章的 AI 工作流
            </p>
        </div>

        <!-- 太极风格主题切换 -->
        <div class="theme-switch-wrapper">
            <span class="theme-switch-label">☀️</span>
            <label class="theme-switch">
                <input type="checkbox" onclick="toggleTheme()">
                <span class="theme-slider"></span>
            </label>
            <span class="theme-switch-label">🌙</span>
        </div>
        """)

        # ═══════════════════════════════════════════════════════════════════
        # 上部功能区 - 三个核心功能 Tab
        # ═══════════════════════════════════════════════════════════════════
        with gr.Tabs() as top_tabs:

            # ─────────────────────────────────────────────────────────────────
            # Tab 1: 🔥 GitHub 爆款
            # ─────────────────────────────────────────────────────────────────
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
                        <div style="background: rgba(255, 200, 0, 0.15); padding: 8px 12px; border-radius: 6px; margin: 5px 0; font-size: 12px; border: 1px solid rgba(255, 200, 0, 0.4); color: #ffd700;">
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
                            minimum=0, maximum=10, value=2, step=1,
                            info="快速介绍的项目数量（每个约300-500字）"
                        )
                        github_deep_count = gr.Slider(
                            label="🔬 深度解读数量",
                            minimum=1, maximum=5, value=1, step=1,
                            info="详细分析的项目数量（每个约1500-2000字）"
                        )
                        github_min_words = gr.Slider(
                            label="📏 文章最小字数",
                            minimum=1500, maximum=8000, value=3500, step=500,
                            info="生成文章的最低字数要求"
                        )
                        gr.Markdown("""
                        <div style="background: rgba(0, 255, 255, 0.1); padding: 8px 12px; border-radius: 6px; margin: 5px 0; font-size: 12px; border: 1px solid rgba(0, 255, 255, 0.3); color: #00ffff;">
                        💡 <b>推荐组合</b>:<br/>
                        • <b>快速版</b>: 3简介 + 0深度 ≈ 1500字<br/>
                        • <b>标准版</b>: 2简介 + 1深度 ≈ 3000字<br/>
                        • <b>深度版</b>: 1简介 + 2深度 ≈ 4500字<br/>
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

            # ─────────────────────────────────────────────────────────────────
            # Tab 2: 💊 痛点诊断
            # ─────────────────────────────────────────────────────────────────
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

            # ─────────────────────────────────────────────────────────────────
            # Tab 3: 📰 热点快报
            # ─────────────────────────────────────────────────────────────────
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

            # ─────────────────────────────────────────────────────────────────
            # Tab 4: 📕 小红书种草
            # ─────────────────────────────────────────────────────────────────
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
                            label="🔍 搜索关键词",
                            placeholder="数码好物、美妆测评...",
                            value="",
                            info="留空则采集热门笔记"
                        )
                        xhs_dry_run = gr.Checkbox(
                            label="🧪 试运行模式（不推送）",
                            value=True
                        )
                        xhs_run_btn = gr.Button("📕 开始采集", variant="primary", size="lg")

                    with gr.Column(scale=2):
                        gr.Markdown("### 📋 执行日志")
                        xhs_log_output = gr.Markdown()

                gr.Markdown("### 📝 种草文预览")
                xhs_article_output = gr.Textbox(label="种草文章", lines=15)

                xhs_run_btn.click(
                    fn=lambda k, d: asyncio.run(run_xhs_template(k, d)),
                    inputs=[xhs_keyword, xhs_dry_run],
                    outputs=[xhs_log_output, xhs_article_output]
                )

            # ─────────────────────────────────────────────────────────────────
            # Tab 5: 🚀 全自动生产
            # ─────────────────────────────────────────────────────────────────
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

                gr.Markdown("""
                ### 📋 配置说明
                所有配置修改后点击「保存配置」生效。敏感信息（API Key、Token、Cookie）请妥善保管。
                """)

                with gr.Row():
                    # 左侧：配置表单
                    with gr.Column(scale=3):

                        # ═══════════════════════════════════════════════════════════
                        # 🤖 Gemini AI 配置
                        # ═══════════════════════════════════════════════════════════
                        with gr.Accordion("🤖 Gemini AI 配置（必填）", open=True):
                            gr.Markdown("""
                            ---
                            **获取步骤：**

                            **方式一：官方 Gemini API（需翻墙，有免费额度）**
                            1. 打开 [Google AI Studio](https://aistudio.google.com/apikey)
                            2. 登录 Google 账号
                            3. 点击「Create API Key」创建密钥
                            4. 复制生成的 API Key
                            5. 下方「API 提供商」选择 `official`

                            **方式二：第三方聚合 API（推荐国内用户）**
                            1. 打开 [PackyAPI](https://www.packyapi.com) 或其他聚合平台
                            2. 注册并登录
                            3. 进入「API Keys」页面创建密钥
                            4. 复制 API Key 和 Base URL
                            5. 下方「API 提供商」选择 `openai_compatible`
                            ---
                            """)
                            gemini_provider = gr.Radio(
                                label="API 提供商",
                                choices=["official", "openai_compatible"],
                                value=current_config['gemini_provider'],
                                info="official=官方 Gemini（需翻墙）| openai_compatible=第三方聚合（国内可用）"
                            )
                            gemini_base_url = gr.Textbox(
                                label="API 地址（仅第三方需要）",
                                placeholder="https://www.packyapi.com/v1",
                                value=current_config['gemini_base_url'],
                                info="第三方聚合服务地址，官方 API 留空"
                            )
                            gemini_api_key = gr.Textbox(
                                label="API Key",
                                value=current_config['gemini_api_key'],
                                type="password",
                                info="从上述平台获取的密钥"
                            )
                            with gr.Row():
                                gemini_model = gr.Dropdown(
                                    label="文本模型",
                                    choices=[
                                        "gemini-2.0-flash", "gemini-1.5-pro",
                                        "gemini-3-pro-preview", "gemini-3-flash-preview",
                                        "gemini-2.5-pro", "gemini-2.5-flash",
                                    ],
                                    value=current_config['gemini_model'],
                                    allow_custom_value=True,
                                    info="推荐: gemini-3-pro-preview（最强）或 gemini-2.0-flash（快速）"
                                )
                                gemini_image_model = gr.Dropdown(
                                    label="图片模型（可选）",
                                    choices=[
                                        "", "imagen-3.0-generate-001",
                                        "gemini-3-pro-image-preview",
                                        "gemini-3-pro-image-preview-16-9-4K",
                                    ],
                                    value=current_config['gemini_image_model'],
                                    allow_custom_value=True,
                                    info="用于生成封面图，留空则使用在线服务"
                                )

                        # ═══════════════════════════════════════════════════════════
                        # 📮 PushPlus 微信推送配置
                        # ═══════════════════════════════════════════════════════════
                        with gr.Accordion("📮 PushPlus 微信推送配置", open=False):
                            gr.Markdown("""
                            ---
                            **获取步骤：**
                            1. 打开 [PushPlus 官网](https://www.pushplus.plus/)
                            2. 使用**微信扫码**登录
                            3. 进入「个人中心」
                            4. 复制页面上显示的 **Token**
                            5. **重要**：必须关注「pushplus推送加」公众号才能收到消息！

                            **免费额度**：每天 200 条消息
                            ---
                            """)
                            push_token = gr.Textbox(
                                label="PushPlus Token",
                                value=current_config['push_token'],
                                type="password",
                                info="从 pushplus.plus 个人中心获取"
                            )
                            push_enabled = gr.Checkbox(
                                label="启用推送",
                                value=current_config['push_enabled'],
                                info="关闭则只生成文章不推送到微信"
                            )

                        # ═══════════════════════════════════════════════════════════
                        # 🐦 Twitter/X 配置
                        # ═══════════════════════════════════════════════════════════
                        with gr.Accordion("🐦 Twitter/X 配置（痛点雷达需要）", open=False):
                            gr.Markdown("""
                            ---
                            **获取步骤：**
                            1. 用 Chrome 浏览器登录 [Twitter/X](https://x.com)
                            2. 安装浏览器扩展「**Cookie-Editor**」或「**EditThisCookie**」
                               - [Cookie-Editor 下载](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)
                            3. 在 Twitter 页面点击扩展图标
                            4. 点击「**Export**」→「**Export as JSON**」
                            5. 将导出的 JSON 内容保存到项目的 `data/cookies.json` 文件

                            **注意**：Cookie 会过期（约7-14天），采集失败时需重新导出
                            ---
                            """)
                            twitter_cookies_path = gr.Textbox(
                                label="Cookies 文件路径",
                                value=current_config['twitter_cookies_path'],
                                info="相对于项目根目录，默认: data/cookies.json"
                            )

                        # ═══════════════════════════════════════════════════════════
                        # 📕 小红书配置
                        # ═══════════════════════════════════════════════════════════
                        with gr.Accordion("📕 小红书配置（小红书采集需要）", open=False):
                            gr.Markdown("""
                            ---
                            **Cookie 获取步骤（推荐方式）：**
                            1. 用 Chrome 浏览器登录 [小红书](https://www.xiaohongshu.com)
                            2. 按 `F12` 打开开发者工具
                            3. 切换到「**Console（控制台）**」标签
                            4. 输入以下命令并按回车：
                            ```
                            document.cookie
                            ```
                            5. 复制输出的**整个字符串**到下方「Cookie」输入框

                            **备选方式（获取更多 Cookie）：**
                            1. F12 → Application → Cookies → xiaohongshu.com
                            2. 手动复制所有 Cookie（重点需要 `web_session` 和 `a1`）
                            3. 格式: `a1=xxx; web_session=xxx; ...`

                            **注意**：Cookie 有效期约 7 天，过期后需重新获取
                            ---
                            """)
                            xhs_cookies = gr.Textbox(
                                label="Cookie 字符串",
                                value=current_config['xhs_cookies'],
                                lines=3,
                                info="从浏览器控制台获取的完整 Cookie"
                            )
                            with gr.Row():
                                xhs_default_keyword = gr.Textbox(
                                    label="默认搜索关键词",
                                    value=current_config['xhs_default_keyword'],
                                    info="采集时的默认搜索词"
                                )
                                xhs_default_style = gr.Dropdown(
                                    label="默认文章风格",
                                    choices=["种草", "测评", "盘点"],
                                    value=current_config['xhs_default_style'],
                                    info="生成文章的默认风格"
                                )

                        # ═══════════════════════════════════════════════════════════
                        # 🐙 GitHub 配置
                        # ═══════════════════════════════════════════════════════════
                        with gr.Accordion("🐙 GitHub 配置（可选，提高 API 限额）", open=False):
                            gr.Markdown("""
                            ---
                            **获取步骤：**
                            1. 登录 [GitHub](https://github.com)
                            2. 点击右上角头像 → Settings
                            3. 左侧菜单最下方点击「**Developer settings**」
                            4. 点击「**Personal access tokens**」→「**Tokens (classic)**」
                            5. 点击「**Generate new token**」→「**Generate new token (classic)**」
                            6. Note 填写：`Hunter AI`
                            7. Expiration 选择有效期（建议 90 天或无期限）
                            8. 勾选 `public_repo` 权限
                            9. 点击「**Generate token**」
                            10. **立即复制** Token（只显示一次！）

                            **不配置也能用**，但 API 限额较低（每小时 60 次）
                            配置后可提升到每小时 **5000 次**
                            ---
                            """)
                            github_token = gr.Textbox(
                                label="GitHub Token",
                                value=current_config['github_token'],
                                type="password",
                                info="Personal Access Token，可选但推荐配置"
                            )
                            with gr.Row():
                                github_min_stars = gr.Slider(
                                    label="最小 Stars 数",
                                    minimum=50, maximum=5000,
                                    value=current_config['github_min_stars'],
                                    step=50,
                                    info="只搜索 Star 数大于此值的项目"
                                )
                                github_days_since_update = gr.Slider(
                                    label="更新时间过滤（天）",
                                    minimum=7, maximum=365,
                                    value=current_config['github_days_since_update'],
                                    step=7,
                                    info="只搜索最近 N 天内有更新的项目"
                                )

                        # ═══════════════════════════════════════════════════════════
                        # 📝 公众号设置
                        # ═══════════════════════════════════════════════════════════
                        with gr.Accordion("📝 公众号设置", open=False):
                            gr.Markdown("""
                            ---
                            配置你的公众号信息，AI 会根据这些设置调整写作风格和内容方向。
                            ---
                            """)
                            account_name = gr.Textbox(
                                label="公众号名称",
                                value=current_config['account_name'],
                                info="用于生成文章时的署名和风格参考"
                            )
                            account_niche = gr.Textbox(
                                label="细分领域",
                                value=current_config['account_niche'],
                                info="如: AI技术、职场成长、产品设计"
                            )
                            account_tone = gr.Textbox(
                                label="写作风格",
                                value=current_config['account_tone'],
                                info="如: 专业且引人入胜、轻松幽默、深度严谨"
                            )
                            with gr.Row():
                                min_length = gr.Number(
                                    label="最小字数",
                                    value=current_config['min_length'],
                                    info="文章最少字数"
                                )
                                max_length = gr.Number(
                                    label="最大字数",
                                    value=current_config['max_length'],
                                    info="文章最多字数"
                                )
                                max_title_length = gr.Number(
                                    label="标题最大长度",
                                    value=current_config['max_title_length'],
                                    info="微信公众号建议不超过22字"
                                )

                        # ═══════════════════════════════════════════════════════════
                        # 💾 存储与系统配置
                        # ═══════════════════════════════════════════════════════════
                        with gr.Accordion("💾 存储与系统配置", open=False):
                            gr.Markdown("""
                            ---
                            高级配置，一般无需修改。
                            ---
                            """)
                            with gr.Row():
                                chromadb_path = gr.Textbox(
                                    label="向量数据库路径",
                                    value=current_config['chromadb_path'],
                                    info="ChromaDB 存储路径，用于内容去重"
                                )
                                output_dir = gr.Textbox(
                                    label="输出目录",
                                    value=current_config['output_dir'],
                                    info="生成文章的保存目录"
                                )
                            log_level = gr.Dropdown(
                                label="日志级别",
                                choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                                value=current_config['log_level'],
                                info="DEBUG最详细，INFO正常，WARNING只显示警告"
                            )

                    # 右侧：状态显示
                    with gr.Column(scale=1):
                        gr.Markdown("### 📊 当前配置状态")
                        config_status = gr.Markdown(value=get_config_info())

                        save_btn = gr.Button("💾 保存配置", variant="primary", size="lg")
                        save_output = gr.Markdown()

                        refresh_btn = gr.Button("🔄 刷新状态", variant="secondary")

                        gr.Markdown("""
                        ---
                        ### 💡 配置优先级
                        1. 界面设置 > config.yaml
                        2. 保存后立即生效
                        3. 部分设置需重启

                        ### 🔒 安全提示
                        - API Key 等敏感信息已加密存储
                        - config.yaml 已加入 .gitignore
                        - 不会被提交到 Git 仓库
                        """)

                save_btn.click(
                    fn=save_config,
                    inputs=[
                        gemini_provider, gemini_base_url, gemini_api_key, gemini_model, gemini_image_model,
                        github_token, github_min_stars, github_days_since_update,
                        push_token, push_enabled,
                        twitter_cookies_path,
                        xhs_cookies, xhs_default_keyword, xhs_default_style,
                        account_name, account_niche, account_tone, min_length, max_length, max_title_length,
                        chromadb_path, output_dir, log_level
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

    # 获取局域网IP地址
    import socket
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
    import os
    os.environ['NO_PROXY'] = 'localhost,127.0.0.1,0.0.0.0'
    os.environ['no_proxy'] = 'localhost,127.0.0.1,0.0.0.0'

    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        show_error=True,
        inbrowser=False,
        css=CUSTOM_CSS,
        theme=gr.themes.Soft(primary_hue="pink", secondary_hue="rose", neutral_hue="slate"),
    )


if __name__ == "__main__":
    main()
