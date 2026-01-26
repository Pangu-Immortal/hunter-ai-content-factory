"""
Hunter AI 内容工厂 - 业务处理函数

包含所有模板运行函数和工具函数：
- run_github_template: GitHub 爆款生成
- run_pain_template: 痛点诊断
- run_news_template: 热点快报
- run_xhs_template: 小红书种草
- run_auto_template: 全自动生产
- run_content_check: 违禁词检查
- run_content_clean: AI 痕迹清理
- get_config_info: 获取配置信息
- save_config: 保存配置
"""

from datetime import datetime
from pathlib import Path

import gradio as gr

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent.parent


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
    keyword: str, min_stars: int, brief_count: int, deep_count: int, min_words: int, dry_run: bool
):
    """
    🔥 GitHub 爆款 - 运行 GitHub 热门项目推荐模板

    流程：GitHub Search API → 筛选项目 → 去重 → AI 生成自定义结构文章
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

        from src.templates.github_template import GitHubTemplate

        logs.append("\n### 🔍 Step 2: 抓取热门项目\n")
        logs.append(f"- 正在查询 GitHub 「{search_keyword}」 热门项目...\n")
        logs.append(f"- 需要抓取: **{brief_count + deep_count}** 个项目\n")
        logs.append("- 🔄 支持自动关键词切换（项目不足时尝试相近关键词）\n")

        # 使用 GitHubTemplate 并传递关键词
        template = GitHubTemplate(keyword=search_keyword)
        result = await template.run()

        logs.append("- ✅ 项目抓取完成\n")
        logs.append("\n### 🤖 Step 3: AI 生成文章\n")
        logs.append("- 正在调用 AI 模型...\n")
        logs.append(f"- 📝 文章结构: **{brief_count}个简介 + {deep_count}个深度解读**\n")
        logs.append(f"- 📏 最小字数: **{min_words}** 字\n")

        if result and result.success:
            word_count = len(result.content)
            logs.append("\n### ✅ 生成完成！\n")
            logs.append(f"- **标题**: {result.title}\n")
            logs.append(f"- **字数**: {word_count} 字 {'✅' if word_count >= min_words else '⚠️ 未达标'}\n")
            logs.append(f"- **关键词**: {search_keyword}\n")
            logs.append(f"- **推送**: {'已禁用（试运行模式）' if dry_run else result.push_status}\n")
            return "\n".join(logs), result.content
        else:
            error_msg = result.error if result else "未知错误"
            logs.append("\n### ⚠️ 执行完成（有问题）\n")
            logs.append(f"- 错误: {error_msg}\n")
            return "\n".join(logs), ""

    except ImportError as e:
        logs.append("\n### ❌ 模块导入失败\n")
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
            logs.append("\n### ⚠️ 执行完成（有问题）\n")
            logs.append(f"- 错误: {error_msg}\n")
            return "\n".join(logs), ""

    except ImportError as e:
        logs.append("\n### ❌ 模块导入失败\n")
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
            logs.append("\n### ⚠️ 执行完成（有问题）\n")
            logs.append(f"- 错误: {error_msg}\n")
            return "\n".join(logs), ""

    except ImportError as e:
        logs.append("\n### ❌ 模块导入失败\n")
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
            logs.append("\n### ⚠️ 执行完成（有问题）\n")
            logs.append(f"- 错误: {error_msg}\n")
            return "\n".join(logs), ""

    except ImportError as e:
        logs.append("\n### ❌ 模块导入失败\n")
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
            logs.append("\n### ⚠️ 执行完成（有问题）\n")
            logs.append(f"- 错误: {error_msg}\n")
            return "\n".join(logs), ""

    except ImportError as e:
        logs.append("\n### ❌ 模块导入失败\n")
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
        from src.config import settings
        from src.utils.content_filter import ContentFilter

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
        from src.config import settings
        from src.utils.content_filter import ContentFilter

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
        from src.config import get_config_status, get_settings

        get_settings.cache_clear()
        settings = get_settings()
        status = get_config_status()

        # 状态图标
        gemini_ok = "✅" if status["gemini"]["api_key_configured"] else "❌"
        github_ok = "✅" if status["github"]["token_configured"] else "⚪"
        push_ok = "✅" if status["pushplus"]["token_configured"] else "⚪"

        # 检查其他配置
        xhs_ok = "⚪"
        twitter_ok = "⚪"
        try:
            if (
                hasattr(settings, "xiaohongshu")
                and settings.xiaohongshu
                and getattr(settings.xiaohongshu, "cookies", "")
            ):
                xhs_ok = "✅"
        except:
            pass
        try:
            if hasattr(settings, "twitter") and settings.twitter and getattr(settings.twitter, "cookies_path", ""):
                twitter_ok = "✅"
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
        gemini_key = getattr(settings.gemini, "api_key", "") or ""
        gemini_provider = getattr(settings.gemini, "provider", "official")
        gemini_model = getattr(settings.gemini, "model", "")
        gemini_image = getattr(settings.gemini, "image_model", "") or "未配置"
        gemini_base = getattr(settings.gemini, "base_url", "") or "官方API"

        # GitHub 配置
        github_key = getattr(settings.github, "token", "") or ""
        github_stars = getattr(settings.github, "min_stars", 200)
        github_days = (
            getattr(settings.github, "days_since_update", 30) if hasattr(settings.github, "days_since_update") else 30
        )

        # PushPlus 配置
        push_key = getattr(settings.push, "token", "") or ""
        push_enabled = getattr(settings.push, "enabled", False)

        # Twitter 配置
        twitter_path = "data/cookies.json"
        try:
            if hasattr(settings, "twitter") and settings.twitter:
                twitter_path = getattr(settings.twitter, "cookies_path", "data/cookies.json")
        except:
            pass

        # 小红书配置
        xhs_cookies = ""
        xhs_keyword = "AI工具"
        xhs_style = "种草"
        try:
            if hasattr(settings, "xiaohongshu") and settings.xiaohongshu:
                xhs_cookies = getattr(settings.xiaohongshu, "cookies", "") or ""
                xhs_keyword = getattr(settings.xiaohongshu, "default_keyword", "AI工具")
                xhs_style = getattr(settings.xiaohongshu, "default_style", "种草")
        except:
            pass

        # 公众号配置
        acc_name = getattr(settings.account, "name", "")
        acc_niche = getattr(settings.account, "niche", "")
        acc_tone = getattr(settings.account, "tone", "")
        acc_min = getattr(settings.account, "min_length", 1500)
        acc_max = getattr(settings.account, "max_length", 2500)
        acc_title = (
            getattr(settings.account, "max_title_length", 20) if hasattr(settings.account, "max_title_length") else 20
        )

        # 存储配置
        chromadb = "data/chromadb"
        output = "output"
        try:
            if hasattr(settings, "storage") and settings.storage:
                chromadb = getattr(settings.storage, "chromadb_path", "data/chromadb")
                output = getattr(settings.storage, "output_dir", "output")
        except:
            pass

        # 系统配置
        log_level = "INFO"
        try:
            if hasattr(settings, "system") and settings.system:
                log_level = getattr(settings.system, "log_level", "INFO")
        except:
            pass

        return f"""
**🤖 Gemini AI**
| 项目 | 状态 |
|------|------|
| API Key | {gemini_ok} {mask_key(gemini_key)} |
| 提供商 | {gemini_provider} |
| Base URL | {gemini_base[:25]}{"..." if len(str(gemini_base)) > 25 else ""} |
| 文本模型 | {gemini_model} |
| 图片模型 | {gemini_image} |

**📮 PushPlus 推送**
| 项目 | 状态 |
|------|------|
| Token | {push_ok} {mask_key(push_key)} |
| 推送 | {"✅ 启用" if push_enabled else "⚪ 禁用"} |

**🐦 Twitter/X**
| 项目 | 状态 |
|------|------|
| Cookies | {twitter_ok} |
| 路径 | {twitter_path} |

**📕 小红书**
| 项目 | 状态 |
|------|------|
| Cookie | {xhs_ok} {mask_key(xhs_cookies, 6) if xhs_cookies else "未配置"} |
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
| 风格 | {acc_tone[:8]}{"..." if len(str(acc_tone)) > 8 else ""} |
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
            "gemini_provider": settings.gemini.provider or "official",
            "gemini_base_url": settings.gemini.base_url or "",
            "gemini_api_key": settings.gemini.api_key or "",
            "gemini_model": settings.gemini.model or "gemini-2.0-flash",
            "gemini_image_model": getattr(settings.gemini, "image_model", "") or "",
            # GitHub 配置
            "github_token": settings.github.token or "",
            "github_min_stars": settings.github.min_stars,
            "github_days_since_update": getattr(settings.github, "days_since_update", 30),
            # PushPlus 配置
            "push_token": settings.push.token or "",
            "push_enabled": settings.push.enabled,
            # Twitter/X 配置
            "twitter_cookies_path": getattr(settings, "twitter", {}).get("cookies_path", "data/cookies.json")
            if hasattr(settings, "twitter")
            else "data/cookies.json",
            # 小红书配置
            "xhs_cookies": getattr(settings, "xiaohongshu", {}).get("cookies", "")
            if hasattr(settings, "xiaohongshu")
            else "",
            "xhs_default_keyword": getattr(settings, "xiaohongshu", {}).get("default_keyword", "AI工具")
            if hasattr(settings, "xiaohongshu")
            else "AI工具",
            "xhs_default_style": getattr(settings, "xiaohongshu", {}).get("default_style", "种草")
            if hasattr(settings, "xiaohongshu")
            else "种草",
            # 公众号设置
            "account_name": settings.account.name or "AI技术前沿",
            "account_niche": settings.account.niche or "AI技术",
            "account_tone": settings.account.tone or "专业且引人入胜",
            "min_length": settings.account.min_length,
            "max_length": settings.account.max_length,
            "max_title_length": getattr(settings.account, "max_title_length", 20),
            # 存储配置
            "chromadb_path": getattr(settings, "storage", {}).get("chromadb_path", "data/chromadb")
            if hasattr(settings, "storage")
            else "data/chromadb",
            "output_dir": getattr(settings, "storage", {}).get("output_dir", "output")
            if hasattr(settings, "storage")
            else "output",
            # 系统配置
            "log_level": getattr(settings, "system", {}).get("log_level", "INFO")
            if hasattr(settings, "system")
            else "INFO",
        }
    except Exception:
        return {
            "gemini_provider": "official",
            "gemini_base_url": "",
            "gemini_api_key": "",
            "gemini_model": "gemini-2.0-flash",
            "gemini_image_model": "",
            "github_token": "",
            "github_min_stars": 200,
            "github_days_since_update": 30,
            "push_token": "",
            "push_enabled": True,
            "twitter_cookies_path": "data/cookies.json",
            "xhs_cookies": "",
            "xhs_default_keyword": "AI工具",
            "xhs_default_style": "种草",
            "account_name": "AI技术前沿",
            "account_niche": "AI技术",
            "account_tone": "专业且引人入胜",
            "min_length": 1500,
            "max_length": 2500,
            "max_title_length": 20,
            "chromadb_path": "data/chromadb",
            "output_dir": "output",
            "log_level": "INFO",
        }


def save_config(
    gemini_provider,
    gemini_base_url,
    gemini_api_key,
    gemini_model,
    gemini_image_model,
    github_token,
    github_min_stars,
    github_days_since_update,
    push_token,
    push_enabled,
    twitter_cookies_path,
    xhs_cookies,
    xhs_default_keyword,
    xhs_default_style,
    account_name,
    account_niche,
    account_tone,
    min_length,
    max_length,
    max_title_length,
    chromadb_path,
    output_dir,
    log_level,
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
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}

        # 更新 Gemini 配置
        config.setdefault("gemini", {})
        config["gemini"]["provider"] = gemini_provider
        config["gemini"]["base_url"] = gemini_base_url
        config["gemini"]["api_key"] = gemini_api_key
        config["gemini"]["model"] = gemini_model
        config["gemini"]["image_model"] = gemini_image_model

        # 更新 GitHub 配置
        config.setdefault("github", {})
        config["github"]["token"] = github_token
        config["github"]["min_stars"] = int(github_min_stars)
        config["github"]["days_since_update"] = int(github_days_since_update)

        # 更新 PushPlus 配置
        config.setdefault("pushplus", {})
        config["pushplus"]["token"] = push_token
        config["pushplus"]["enabled"] = push_enabled

        # 更新 Twitter 配置
        config.setdefault("twitter", {})
        config["twitter"]["cookies_path"] = twitter_cookies_path

        # 更新小红书配置
        config.setdefault("xiaohongshu", {})
        config["xiaohongshu"]["cookies"] = xhs_cookies
        config["xiaohongshu"]["default_keyword"] = xhs_default_keyword
        config["xiaohongshu"]["default_style"] = xhs_default_style

        # 更新公众号配置
        config.setdefault("account", {})
        config["account"]["name"] = account_name
        config["account"]["niche"] = account_niche
        config["account"]["tone"] = account_tone
        config["account"]["min_length"] = int(min_length)
        config["account"]["max_length"] = int(max_length)
        config["account"]["max_title_length"] = int(max_title_length)

        # 更新存储配置
        config.setdefault("storage", {})
        config["storage"]["chromadb_path"] = chromadb_path
        config["storage"]["output_dir"] = output_dir

        # 更新系统配置
        config.setdefault("system", {})
        config["system"]["log_level"] = log_level

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        from src.config import get_settings

        get_settings.cache_clear()

        return "✅ **配置已保存！** 部分设置需重启生效。"

    except Exception as e:
        return f"❌ 保存失败: {str(e)}"
