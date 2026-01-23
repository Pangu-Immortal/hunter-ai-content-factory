"""
Hunter AI 内容工厂 - 自动创作模板

功能：
- 步骤1: Intel 聚合采集（GitHub Trending, Twitter, HackerNews, Reddit, 小红书）
- 步骤2: AI 分析（选题判断、痛点诊断、内容提炼、结构化写作）
- 步骤3: 内容生成（公众号文章 MD、微信推送）

使用方法：
    from src.templates import get_template
    template = get_template("auto")
    result = await template.run()

命令行：
    uv run hunter run -t auto

GitHub: https://github.com/Pangu-Immortal/hunter-ai-content-factory
Author: Pangu-Immortal
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from src.templates import BaseTemplate, TemplateResult, register_template
from src.intel.utils import (
    get_output_path,
    get_today_str,
    push_to_wechat,
    create_article_dir,
    get_article_file_path,
    get_chromadb_client,
)
from src.config import settings
from src.utils.ai_client import get_ai_client

# 终端输出美化
console = Console()


@dataclass
class IntelData:
    """情报数据结构"""
    source: str           # 来源平台
    title: str            # 标题/摘要
    content: str          # 内容
    url: str = ""         # 原始链接
    author: str = ""      # 作者
    score: int = 0        # 热度分数
    tags: list[str] = field(default_factory=list)  # 标签
    images: list[str] = field(default_factory=list)  # 图片 URL 列表（封面图、截图等）


@dataclass
class AnalysisResult:
    """AI 分析结果"""
    selected_topic: str       # 选定的主题
    topic_reason: str         # 选题理由
    pain_points: list[str]    # 提炼的痛点
    key_insights: list[str]   # 核心洞察
    content_outline: str      # 内容大纲
    target_audience: str      # 目标读者


@register_template("auto")
class AutoTemplate(BaseTemplate):
    """
    自动创作模板

    完整的 3 步流水线：
    1. Intel 采集：从 5 个平台聚合内容
    2. AI 分析：选题、诊断、提炼
    3. 内容生成：MD 文章 + 微信推送
    """

    name = "auto"
    description = "自动创作 - 全自动 Intel→分析→生成 流水线"
    requires_intel = True

    def __init__(self, topic: str = None, platforms: list[str] = None):
        """
        初始化自动创作模板

        Args:
            topic: 指定主题（可选，不指定则自动选题）
            platforms: 指定采集平台（默认全部）
        """
        super().__init__()
        self.topic = topic
        self.platforms = platforms or ["hackernews", "twitter", "reddit", "github", "xiaohongshu"]
        self.intel_data: list[IntelData] = []
        self.analysis_result: Optional[AnalysisResult] = None
        self.ai_client = None
        self._init_ai_client()
        self._init_chromadb()

    def _init_ai_client(self):
        """初始化 AI 客户端"""
        if settings.gemini.api_key:
            self.ai_client = get_ai_client()
            provider = "第三方聚合" if settings.gemini.is_openai_compatible else "官方 Gemini"
            console.print(f"[green]✅ AI 客户端连接成功 ({provider})[/green]")

    def _init_chromadb(self):
        """初始化 ChromaDB"""
        try:
            client = get_chromadb_client()
            self.collection = client.get_or_create_collection(name="auto_creation")
            console.print("[green]✅ ChromaDB 数据库连接成功[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠️ ChromaDB 初始化失败: {e}[/yellow]")
            self.collection = None

    # ═══════════════════════════════════════════════════════════════════════════════
    # 步骤 1: Intel 聚合采集
    # ═══════════════════════════════════════════════════════════════════════════════

    async def step1_collect_intel(self) -> list[IntelData]:
        """
        步骤 1: 从多平台聚合采集内容

        Returns:
            list[IntelData]: 采集到的情报列表
        """
        console.print(Panel("[bold cyan]📡 步骤 1: Intel 聚合采集[/bold cyan]", expand=False))

        intel_list = []

        # GitHub Trending
        if "github" in self.platforms:
            github_intel = await self._collect_github()
            intel_list.extend(github_intel)

        # HackerNews
        if "hackernews" in self.platforms:
            hn_intel = await self._collect_hackernews()
            intel_list.extend(hn_intel)

        # Twitter
        if "twitter" in self.platforms:
            twitter_intel = await self._collect_twitter()
            intel_list.extend(twitter_intel)

        # Reddit
        if "reddit" in self.platforms:
            reddit_intel = await self._collect_reddit()
            intel_list.extend(reddit_intel)

        # 小红书
        if "xiaohongshu" in self.platforms:
            xhs_intel = await self._collect_xiaohongshu()
            intel_list.extend(xhs_intel)

        console.print(f"\n[green]📊 共采集 {len(intel_list)} 条情报[/green]")
        self.intel_data = intel_list
        return intel_list

    async def _collect_github(self) -> list[IntelData]:
        """采集 GitHub Trending"""
        console.print("\n[cyan]🐙 采集 GitHub Trending...[/cyan]")
        intel = []

        try:
            from src.intel.github_trending import GitHubTrendingHunter

            hunter = GitHubTrendingHunter()
            projects = await hunter.fetch_trending(since="daily")

            for p in projects[:8]:
                # 使用 Socialify 服务生成项目卡片图
                socialify_url = (
                    f"https://socialify.git.ci/{p.name}/image"
                    f"?description=1&font=Inter&language=1&name=1&owner=1"
                    f"&pattern=Plus&stargazers=1&theme=Auto"
                )
                intel.append(IntelData(
                    source="GitHub",
                    title=p.name,
                    content=f"{p.description} | Stars: {p.stars}",
                    url=p.url,
                    author=p.name.split("/")[0],
                    score=p.stars,
                    tags=p.topics[:5],
                    images=[socialify_url],  # GitHub 使用 Socialify 生成项目封面
                ))

            console.print(f"  ✅ GitHub: {len(intel)} 条")

        except Exception as e:
            console.print(f"  [yellow]⚠️ GitHub 采集失败: {e}[/yellow]")

        return intel

    async def _collect_hackernews(self) -> list[IntelData]:
        """采集 HackerNews"""
        console.print("\n[cyan]🔥 采集 HackerNews...[/cyan]")
        intel = []

        try:
            from src.intel.utils import create_http_client

            http = create_http_client(timeout=15.0)
            response = http.get('https://hacker-news.firebaseio.com/v0/topstories.json')
            top_ids = response.json()[:10]

            for item_id in top_ids:
                item = http.get(f'https://hacker-news.firebaseio.com/v0/item/{item_id}.json').json()
                if item and item.get('score', 0) >= 50:
                    intel.append(IntelData(
                        source="HackerNews",
                        title=item.get('title', ''),
                        content=item.get('title', ''),
                        url=item.get('url', ''),
                        author=item.get('by', ''),
                        score=item.get('score', 0),
                    ))

            http.close()
            console.print(f"  ✅ HackerNews: {len(intel)} 条")

        except Exception as e:
            console.print(f"  [yellow]⚠️ HackerNews 采集失败: {e}[/yellow]")

        return intel

    async def _collect_twitter(self) -> list[IntelData]:
        """采集 Twitter"""
        console.print("\n[cyan]🐦 采集 Twitter...[/cyan]")
        intel = []

        try:
            import json
            from twikit import Client as TwitterClient

            cookies_file = settings.twitter.cookies_file
            if not cookies_file.exists():
                console.print("  [yellow]⚠️ Twitter Cookies 未配置[/yellow]")
                return intel

            client = TwitterClient(language='en-US')

            with open(cookies_file, 'r', encoding='utf-8') as f:
                cookies_data = json.load(f)

            if isinstance(cookies_data, list):
                cookies_dict = {c['name']: c['value'] for c in cookies_data if 'name' in c}
                client.set_cookies(cookies_dict)
            else:
                client.set_cookies(cookies_data)

            keywords = ["AI tools", "ChatGPT", "LLM", "AI agent"]
            for kw in keywords[:2]:
                tweets = await client.search_tweet(kw, product='Latest', count=3)
                for tweet in tweets or []:
                    # 尝试获取推文媒体图片
                    images = []
                    if hasattr(tweet, 'media') and tweet.media:
                        for media in tweet.media:
                            if hasattr(media, 'media_url_https'):
                                images.append(media.media_url_https)
                            elif hasattr(media, 'url'):
                                images.append(media.url)

                    intel.append(IntelData(
                        source="Twitter",
                        title=tweet.text[:50],
                        content=tweet.text,
                        url=f"https://twitter.com/i/status/{tweet.id}",
                        author=tweet.user.name if tweet.user else "Unknown",
                        tags=[kw],
                        images=images,  # Twitter 推文媒体图片
                    ))

            console.print(f"  ✅ Twitter: {len(intel)} 条")

        except Exception as e:
            console.print(f"  [yellow]⚠️ Twitter 采集失败: {e}[/yellow]")

        return intel

    async def _collect_reddit(self) -> list[IntelData]:
        """采集 Reddit"""
        console.print("\n[cyan]🔴 采集 Reddit...[/cyan]")
        intel = []

        try:
            from src.intel.reddit_hunter import RedditHunter

            hunter = RedditHunter(mode="trending")
            await hunter.run()

            for post in hunter.posts[:8]:
                # 收集缩略图（如果有）
                images = [post.thumbnail] if post.thumbnail else []
                intel.append(IntelData(
                    source="Reddit",
                    title=post.title,
                    content=f"{post.title} | {post.selftext[:200] if post.selftext else ''}",
                    url=post.permalink,
                    author=post.author,
                    score=post.score,
                    tags=[f"r/{post.subreddit}"],
                    images=images,  # Reddit 帖子缩略图
                ))

            console.print(f"  ✅ Reddit: {len(intel)} 条")

        except Exception as e:
            console.print(f"  [yellow]⚠️ Reddit 采集失败: {e}[/yellow]")

        return intel

    async def _collect_xiaohongshu(self) -> list[IntelData]:
        """采集小红书"""
        console.print("\n[cyan]📕 采集小红书...[/cyan]")
        intel = []

        try:
            from src.intel.xiaohongshu_browser import XiaohongshuBrowser

            hunter = XiaohongshuBrowser()
            if not hunter.is_logged_in():
                console.print("  [yellow]⚠️ 小红书未登录[/yellow]")
                return intel

            notes = await hunter.search(keyword="AI工具", count=5)

            for note in notes:
                # 支持 XhsNote 对象和字典两种格式
                if hasattr(note, 'title'):
                    # XhsNote 对象
                    intel.append(IntelData(
                        source="小红书",
                        title=note.title,
                        content=note.desc[:200] if note.desc else "",
                        url=note.url or f"https://www.xiaohongshu.com/explore/{note.note_id}",
                        author=note.author,
                        score=note.likes,
                        images=note.images,  # 小红书笔记图片列表
                    ))
                else:
                    # 字典格式（兼容旧版本）
                    intel.append(IntelData(
                        source="小红书",
                        title=note.get("title", ""),
                        content=note.get("desc", "")[:200],
                        url=note.get("url", f"https://www.xiaohongshu.com/explore/{note.get('note_id', '')}"),
                        author=note.get("author", ""),
                        score=note.get("likes", 0),
                        images=note.get("images", []),  # 小红书笔记图片列表
                    ))

            console.print(f"  ✅ 小红书: {len(intel)} 条")

        except Exception as e:
            console.print(f"  [yellow]⚠️ 小红书采集失败: {e}[/yellow]")

        return intel

    # ═══════════════════════════════════════════════════════════════════════════════
    # 步骤 2: AI 分析
    # ═══════════════════════════════════════════════════════════════════════════════

    async def step2_ai_analysis(self) -> AnalysisResult:
        """
        步骤 2: AI 分析采集的内容

        - 选题判断：从众多内容中选出最有价值的主题
        - 痛点诊断：提炼用户痛点和需求
        - 内容提炼：萃取核心洞察
        """
        console.print(Panel("[bold cyan]🧠 步骤 2: AI 智能分析[/bold cyan]", expand=False))

        if not self.ai_client:
            raise ValueError("AI 客户端未初始化")

        # 格式化情报数据
        intel_text = self._format_intel_for_analysis()

        # AI 分析 prompt
        prompt = f"""
# Role: 内容策略分析师
你是一位专业的内容策略分析师，擅长从海量信息中发现有价值的选题和洞察。

# Task
分析以下从多个平台采集的情报，完成：
1. **选题判断**：选出最有潜力的主题
2. **痛点诊断**：提炼用户的核心痛点
3. **内容提炼**：萃取可用于文章的核心洞察
4. **大纲设计**：设计文章结构

# Input Data
{intel_text}

# Output Format (请严格按此格式输出)

## 选定主题
[一句话描述选定的主题]

## 选题理由
[2-3 句话解释为什么选择这个主题]

## 核心痛点
1. [痛点 1]
2. [痛点 2]
3. [痛点 3]

## 核心洞察
1. [洞察 1]
2. [洞察 2]
3. [洞察 3]

## 目标读者
[描述目标读者画像]

## 文章大纲
1. 引言（抓住注意力）
2. 问题描述（共鸣）
3. 解决方案（价值）
4. 实操指南（可执行）
5. 总结（行动号召）
"""

        console.print("[cyan]🤔 AI 正在分析情报...[/cyan]")

        try:
            response = self.ai_client.generate_sync(prompt)
            analysis_text = response.text

            # 解析分析结果
            result = self._parse_analysis(analysis_text)
            self.analysis_result = result

            console.print(f"\n[green]✅ 分析完成[/green]")
            console.print(f"   📌 选题: {result.selected_topic}")
            console.print(f"   🎯 痛点: {len(result.pain_points)} 个")
            console.print(f"   💡 洞察: {len(result.key_insights)} 个")

            return result

        except Exception as e:
            console.print(f"[red]❌ AI 分析失败: {e}[/red]")
            raise

    def _format_intel_for_analysis(self) -> str:
        """格式化情报数据供 AI 分析"""
        lines = []
        for i, intel in enumerate(self.intel_data, 1):
            lines.append(f"### 情报 {i} [{intel.source}]")
            lines.append(f"- 标题: {intel.title}")
            lines.append(f"- 内容: {intel.content[:200]}")
            if intel.score:
                lines.append(f"- 热度: {intel.score}")
            if intel.tags:
                lines.append(f"- 标签: {', '.join(intel.tags[:3])}")
            lines.append("")
        return "\n".join(lines)

    def _parse_analysis(self, text: str) -> AnalysisResult:
        """解析 AI 分析结果"""
        import re

        # 提取各部分
        topic_match = re.search(r'## 选定主题\n(.+?)(?=\n##|\Z)', text, re.DOTALL)
        reason_match = re.search(r'## 选题理由\n(.+?)(?=\n##|\Z)', text, re.DOTALL)
        pain_match = re.search(r'## 核心痛点\n(.+?)(?=\n##|\Z)', text, re.DOTALL)
        insight_match = re.search(r'## 核心洞察\n(.+?)(?=\n##|\Z)', text, re.DOTALL)
        audience_match = re.search(r'## 目标读者\n(.+?)(?=\n##|\Z)', text, re.DOTALL)
        outline_match = re.search(r'## 文章大纲\n(.+?)(?=\n##|\Z)', text, re.DOTALL)

        def extract_list(text: str) -> list[str]:
            items = re.findall(r'\d+\.\s*(.+)', text)
            return items

        return AnalysisResult(
            selected_topic=topic_match.group(1).strip() if topic_match else "AI 热门话题",
            topic_reason=reason_match.group(1).strip() if reason_match else "",
            pain_points=extract_list(pain_match.group(1)) if pain_match else [],
            key_insights=extract_list(insight_match.group(1)) if insight_match else [],
            target_audience=audience_match.group(1).strip() if audience_match else "AI 爱好者",
            content_outline=outline_match.group(1).strip() if outline_match else "",
        )

    # ═══════════════════════════════════════════════════════════════════════════════
    # 步骤 3: 内容生成
    # ═══════════════════════════════════════════════════════════════════════════════

    async def step3_generate_content(self) -> tuple[str, str, Path]:
        """
        步骤 3: 生成内容

        Returns:
            tuple: (文章标题, 文章内容, 文章目录路径)
        """
        import json

        console.print(Panel("[bold cyan]✍️ 步骤 3: 内容生成[/bold cyan]", expand=False))

        if not self.analysis_result:
            raise ValueError("分析结果为空，请先执行步骤 2")

        # 生成文章
        article_title, article_content = await self._generate_article()

        # 创建文章目录
        article_dir = create_article_dir(article_title)

        # 保存 Markdown
        md_path = get_article_file_path(article_dir, "article.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# {article_title}\n\n{article_content}")
        console.print(f"[green]📝 MD 文章已保存: {md_path}[/green]")

        # 收集所有图片 URL（从 intel_data 中提取）
        all_images = []
        for intel in self.intel_data:
            if intel.images:
                all_images.extend(intel.images)

        # 保存元数据（包含图片列表）
        metadata_path = get_article_file_path(article_dir, "metadata.json")
        metadata = {
            "title": article_title,
            "date": get_today_str(),
            "topic": self.analysis_result.selected_topic if self.analysis_result else "",
            "platforms": self.platforms,
            "intel_count": len(self.intel_data),
            "cover_images": all_images[:10],  # 保留前 10 张图片作为封面候选
            "intel_sources": [
                {
                    "source": intel.source,
                    "title": intel.title,
                    "url": intel.url,
                    "images": intel.images,
                }
                for intel in self.intel_data[:10]  # 保留前 10 条情报的详细信息
            ]
        }
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        console.print(f"[green]📋 元数据已保存: {metadata_path}[/green]")
        console.print(f"[green]📷 封面图数量: {len(all_images[:10])}[/green]")

        # 保存到数据库
        self._save_to_db(article_title, article_content)

        return article_title, article_content, article_dir

    async def _generate_article(self) -> tuple[str, str]:
        """使用 AI 生成文章"""
        console.print("[cyan]✍️ AI 正在撰写文章...[/cyan]")

        analysis = self.analysis_result
        intel_examples = "\n".join([
            f"- [{i.source}] {i.title}" for i in self.intel_data[:5]
        ])

        prompt = f"""
# Role: 公众号爆款写手
你是一位擅长写公众号文章的写手，文风轻松有趣，观点独到，能把复杂的技术概念讲得通俗易懂。

# Task
根据以下选题和分析，写一篇 1500-2000 字的公众号文章。

# 选题信息
- 主题: {analysis.selected_topic}
- 选题理由: {analysis.topic_reason}
- 目标读者: {analysis.target_audience}

# 核心痛点
{chr(10).join([f"- {p}" for p in analysis.pain_points])}

# 核心洞察
{chr(10).join([f"- {i}" for i in analysis.key_insights])}

# 内容大纲
{analysis.content_outline}

# 参考素材
{intel_examples}

# 写作要求
1. **标题**：20 字以内，吸引眼球但不标题党
2. **开篇**：用一个生动的场景或问题抓住读者
3. **正文**：
   - 用通俗语言解释复杂概念
   - 结合具体案例和数据
   - 提供可操作的建议
4. **结尾**：引导互动（提问/投票/留言）
5. **禁止使用**：首先、其次、最后、综上所述、值得注意的是
6. **格式**：使用 Markdown，适当用 emoji 增强阅读体验

# 输出格式
直接输出 Markdown 格式的文章，第一行是标题（以 # 开头）
"""

        try:
            response = self.ai_client.generate_sync(prompt)
            article_text = response.text.strip()

            # 提取标题
            lines = article_text.split('\n')
            title = lines[0].replace('#', '').strip() if lines else analysis.selected_topic

            # 提取正文
            content = '\n'.join(lines[1:]).strip() if len(lines) > 1 else article_text

            console.print(f"[green]✅ 文章生成成功: {title}[/green]")
            return title, content

        except Exception as e:
            console.print(f"[red]❌ 文章生成失败: {e}[/red]")
            raise

    def _save_to_db(self, title: str, content: str):
        """保存到数据库"""
        if self.collection is None:
            return

        try:
            today = get_today_str()
            report_id = f"auto_article_{today}_{title[:20]}"

            self.collection.upsert(
                documents=[content],
                metadatas=[{
                    "type": "auto_article",
                    "title": title,
                    "date": today,
                    "topic": self.analysis_result.selected_topic if self.analysis_result else "",
                    "platforms": ",".join(self.platforms),
                }],
                ids=[report_id]
            )
            console.print(f"[green]💾 文章已存入数据库[/green]")

        except Exception as e:
            console.print(f"[yellow]⚠️ 数据库存储失败: {e}[/yellow]")

    # ═══════════════════════════════════════════════════════════════════════════════
    # 主流程
    # ═══════════════════════════════════════════════════════════════════════════════

    async def run(self) -> TemplateResult:
        """
        执行自动创作完整流程

        流程：
        1. Intel 聚合采集（5 平台）
        2. AI 智能分析（选题 + 诊断 + 提炼）
        3. 内容生成（MD + 推送）
        """
        self.print_header()

        console.print(Panel(
            "[bold magenta]🚀 自动创作模式启动[/bold magenta]\n"
            "Intel 采集 → AI 分析 → 内容生成",
            expand=False
        ))

        try:
            # 步骤 1: 采集
            intel_data = await self.step1_collect_intel()

            if not intel_data:
                return TemplateResult(
                    success=False,
                    title="",
                    content="",
                    output_path="",
                    push_status="失败",
                    error="未采集到任何情报",
                )

            # 步骤 2: 分析
            analysis = await self.step2_ai_analysis()

            # 步骤 3: 生成
            title, content, article_dir = await self.step3_generate_content()

            # 推送
            push_status = "未推送"
            if settings.push.enabled:
                success = push_to_wechat(title=f"【AI创作】{title}", content=content)
                push_status = "已推送" if success else "推送失败"

            console.print(Panel(
                f"[bold green]✅ 自动创作完成[/bold green]\n"
                f"📌 主题: {title}\n"
                f"📊 情报: {len(intel_data)} 条\n"
                f"📁 目录: {article_dir}\n"
                f"📤 推送: {push_status}",
                expand=False
            ))

            return TemplateResult(
                success=True,
                title=title,
                content=content,
                output_path=str(article_dir),
                push_status=push_status,
            )

        except Exception as e:
            console.print(f"[red]❌ 自动创作失败: {e}[/red]")
            return TemplateResult(
                success=False,
                title="",
                content="",
                output_path="",
                push_status="失败",
                error=str(e),
            )
