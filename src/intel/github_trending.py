"""
Hunter AI 内容工厂 - GitHub Trending 采集模块

功能：
- 采集 GitHub Trending 上的 AI/ML 热门项目
- 生成「2个项目推荐 + 1个深度解读」格式的文章
- 本地存储已推荐项目，避免重复推荐
- 支持全自动执行流程

使用方法：
    from src.intel.github_trending import GitHubTrendingHunter
    hunter = GitHubTrendingHunter()
    await hunter.run()

GitHub: https://github.com/Pangu-Immortal/hunter-ai-content-factory
Author: Pangu-Immortal
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.config import settings, ROOT_DIR
from src.utils.ai_client import get_ai_client, generate_project_cover
from src.intel.utils import (
    create_http_client,
    get_chromadb_client,
    generate_content_id,
    push_to_wechat,
    get_output_path,
    get_today_str,
    call_with_retry,
    create_article_dir,
    get_article_file_path,
)

# 终端输出美化
console = Console()


@dataclass
class TrendingProject:
    """GitHub Trending 项目数据结构"""
    name: str                    # 项目全名（owner/repo）
    description: str             # 项目描述
    stars: int                   # Star 数
    forks: int                   # Fork 数
    today_stars: int             # 今日新增 Star
    language: str                # 编程语言
    url: str                     # 项目链接
    topics: list[str] = field(default_factory=list)  # 标签


@dataclass
class ArticleContent:
    """文章内容结构"""
    title: str                   # 文章标题
    intro: str                   # 开篇引言
    projects_brief: list[dict]   # 项目简介列表（2个）
    deep_dive: dict              # 深度解读项目
    conclusion: str              # 结尾总结
    full_content: str = ""       # 完整文章内容
    cover_images: list[str] = field(default_factory=list)  # 封面图路径列表


class GitHubTrendingHunter:
    """
    GitHub Trending 猎手

    采集 GitHub Trending 页面的 AI/ML 热门项目，
    生成「2个项目推荐 + 1个深度解读」格式的公众号文章。
    支持本地存储已推荐项目，避免重复推荐。
    """

    # 已推荐项目历史记录文件路径
    HISTORY_FILE = ROOT_DIR / "data" / "recommended_projects.json"

    # 项目冷却期（天数）- 超过此天数后可再次推荐
    COOLDOWN_DAYS = 30

    # AI/ML 相关的过滤关键词
    AI_KEYWORDS = [
        "ai", "ml", "machine-learning", "deep-learning", "neural",
        "llm", "gpt", "transformer", "nlp", "chatbot", "agent",
        "rag", "embedding", "vector", "langchain", "openai",
        "anthropic", "claude", "gemini", "ollama", "llama",
        "diffusion", "stable-diffusion", "midjourney", "image-generation",
        "automation", "workflow", "copilot", "assistant"
    ]

    # 关键词扩展映射 - 当项目不足时自动尝试相近关键词
    KEYWORD_EXPANSION = {
        "ai": ["artificial intelligence", "machine learning", "deep learning", "neural network"],
        "llm": ["large language model", "gpt", "chatbot", "nlp", "transformer"],
        "agent": ["ai agent", "autonomous agent", "llm agent", "multi-agent"],
        "rag": ["retrieval augmented", "vector database", "embedding", "semantic search"],
        "ml": ["machine learning", "deep learning", "tensorflow", "pytorch"],
        "chatbot": ["conversational ai", "chat assistant", "llm chat", "dialogue"],
        "automation": ["workflow automation", "ai automation", "auto", "pipeline"],
        "langchain": ["llm framework", "ai chain", "agent framework", "llm toolkit"],
        "vector": ["vector database", "embedding", "similarity search", "semantic"],
        "diffusion": ["stable diffusion", "image generation", "text to image", "generative"],
        "mcp": ["model context protocol", "claude mcp", "anthropic mcp"],
        "claude": ["anthropic", "claude ai", "sonnet", "opus"],
        "openai": ["gpt", "chatgpt", "openai api", "gpt-4"],
        "gemini": ["google ai", "palm", "bard", "vertex ai"],
    }

    def __init__(self, keyword: str = "AI"):
        """初始化 GitHub Trending 猎手

        Args:
            keyword: 搜索关键词，用于筛选项目类型
        """
        self.keyword = keyword.strip().lower() if keyword else "ai"
        self.tried_keywords = [self.keyword]  # 已尝试的关键词列表
        self.http = create_http_client(timeout=30.0)
        self._init_ai_client()
        self._init_chromadb()  # 初始化 ChromaDB 向量数据库
        self.projects: list[TrendingProject] = []
        self.recommended_history: dict = self._load_history()  # 加载历史推荐记录

    def _init_ai_client(self):
        """初始化 AI 客户端"""
        if not settings.gemini.api_key:
            raise ValueError("AI API Key 未配置")
        self.ai_client = get_ai_client()
        provider = "第三方聚合" if settings.gemini.is_openai_compatible else "官方 Gemini"
        console.print(f"[green]✅ AI 客户端连接成功 ({provider})[/green]")

    def _init_chromadb(self):
        """
        初始化 ChromaDB 向量数据库

        用于存储项目的语义向量，实现基于内容相似度的去重。
        Collection 名称: github_trending_projects
        """
        try:
            client = get_chromadb_client()
            self.collection = client.get_or_create_collection(
                name="github_trending_projects",
                metadata={"description": "GitHub Trending 项目向量存储，用于语义去重"}
            )
            count = self.collection.count()
            console.print(f"[green]✅ ChromaDB 向量数据库连接成功 (已存储 {count} 个项目)[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠️ ChromaDB 初始化失败，将使用 JSON 文件去重: {e}[/yellow]")
            self.collection = None

    def _is_similar_in_chromadb(self, project: "TrendingProject", threshold: float = 0.85) -> bool:
        """
        检查项目是否与已存储的项目语义相似

        使用 ChromaDB 的向量相似度搜索，判断新项目是否与历史项目重复。
        相似度阈值默认 0.85（85% 相似则认为重复）。

        Args:
            project: 待检查的项目
            threshold: 相似度阈值（0-1），越高越严格

        Returns:
            bool: True 表示找到相似项目（应跳过），False 表示无相似项目
        """
        if self.collection is None:
            return False  # ChromaDB 不可用时跳过向量检查

        # 构建项目的文本表示（用于生成向量）
        project_text = f"{project.name} {project.description} {' '.join(project.topics)}"

        try:
            # 使用 ChromaDB 的内置向量化搜索相似项目
            results = self.collection.query(
                query_texts=[project_text],
                n_results=3,  # 返回最相似的 3 个
                include=["distances", "metadatas"]
            )

            if results and results["distances"] and results["distances"][0]:
                # ChromaDB 返回的是 L2 距离，需要转换为相似度
                # 相似度 ≈ 1 / (1 + distance)
                min_distance = min(results["distances"][0])
                similarity = 1 / (1 + min_distance)

                if similarity >= threshold:
                    matched_name = results["metadatas"][0][0].get("name", "未知") if results["metadatas"][0] else "未知"
                    console.print(f"[yellow]🔍 发现相似项目: {project.name} ≈ {matched_name} (相似度: {similarity:.1%})[/yellow]")
                    return True

            return False

        except Exception as e:
            console.print(f"[dim]⚠️ 向量相似度检查失败: {e}[/dim]")
            return False

    def _add_to_chromadb(self, project: "TrendingProject") -> None:
        """
        将项目添加到 ChromaDB 向量数据库

        Args:
            project: 要存储的项目
        """
        if self.collection is None:
            return  # ChromaDB 不可用时跳过

        project_text = f"{project.name} {project.description} {' '.join(project.topics)}"
        project_id = generate_content_id("github", project.name, project.name)

        try:
            # 检查是否已存在
            existing = self.collection.get(ids=[project_id])
            if existing and existing["ids"]:
                # 已存在，更新元数据
                self.collection.update(
                    ids=[project_id],
                    documents=[project_text],
                    metadatas=[{
                        "name": project.name,
                        "stars": project.stars,
                        "language": project.language,
                        "updated_at": datetime.now().isoformat()
                    }]
                )
            else:
                # 新增
                self.collection.add(
                    ids=[project_id],
                    documents=[project_text],
                    metadatas=[{
                        "name": project.name,
                        "stars": project.stars,
                        "language": project.language,
                        "added_at": datetime.now().isoformat()
                    }]
                )
            console.print(f"[dim]💾 已存储到向量数据库: {project.name}[/dim]")

        except Exception as e:
            console.print(f"[dim]⚠️ 存储到向量数据库失败: {e}[/dim]")

    def _load_history(self) -> dict:
        """
        加载已推荐项目历史记录

        Returns:
            dict: 历史记录，格式为 {"projects": [{"name": "owner/repo", "recommended_at": "2026-01-22", "stars": 123}]}
        """
        if self.HISTORY_FILE.exists():
            try:
                with open(self.HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    console.print(f"[dim]📂 已加载 {len(data.get('projects', []))} 条历史推荐记录[/dim]")
                    return data
            except (json.JSONDecodeError, IOError) as e:
                console.print(f"[yellow]⚠️ 历史记录文件损坏，将重新创建: {e}[/yellow]")
        return {"projects": []}

    def _save_history(self, new_projects: list[TrendingProject]) -> None:
        """
        保存新推荐的项目到历史记录

        Args:
            new_projects: 本次推荐的项目列表
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # 添加新推荐的项目
        for project in new_projects:
            # 检查是否已存在（更新推荐日期）
            existing = next(
                (p for p in self.recommended_history["projects"] if p["name"] == project.name),
                None
            )
            if existing:
                existing["recommended_at"] = today  # 更新日期
                existing["stars"] = project.stars  # 更新 star 数
            else:
                self.recommended_history["projects"].append({
                    "name": project.name,
                    "recommended_at": today,
                    "stars": project.stars,
                })

        # 清理过期记录（超过 90 天的记录可以删除以控制文件大小）
        cutoff_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        self.recommended_history["projects"] = [
            p for p in self.recommended_history["projects"]
            if p.get("recommended_at", "2000-01-01") > cutoff_date
        ]

        # 确保目录存在
        self.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

        # 保存到文件
        try:
            with open(self.HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.recommended_history, f, ensure_ascii=False, indent=2)
            console.print(f"[green]💾 已保存 {len(new_projects)} 个项目到历史记录[/green]")
        except IOError as e:
            console.print(f"[red]❌ 保存历史记录失败: {e}[/red]")

        # 同时存储到 ChromaDB 向量数据库（用于语义去重）
        for project in new_projects:
            self._add_to_chromadb(project)

    def _is_recently_recommended(self, project_name: str) -> bool:
        """
        检查项目是否在冷却期内被推荐过

        Args:
            project_name: 项目名称（owner/repo 格式）

        Returns:
            bool: 如果在冷却期内被推荐过返回 True
        """
        cutoff_date = (datetime.now() - timedelta(days=self.COOLDOWN_DAYS)).strftime("%Y-%m-%d")

        for record in self.recommended_history.get("projects", []):
            if record.get("name") == project_name:
                recommended_at = record.get("recommended_at", "2000-01-01")
                if recommended_at > cutoff_date:  # 在冷却期内
                    return True
        return False

    async def fetch_trending(self, language: str = "", since: str = "daily") -> list[TrendingProject]:
        """
        获取 GitHub Trending 项目列表

        优先使用 GitHub 官方 Search API（更稳定），
        按最近更新时间 + 高星数筛选热门项目

        Args:
            language: 编程语言过滤（空字符串表示所有语言）
            since: 时间范围（daily/weekly/monthly）

        Returns:
            list[TrendingProject]: 项目列表
        """
        console.print(f"[cyan]🔍 获取 GitHub 热门项目 ({since})...[/cyan]")

        # 直接使用 GitHub Search API（官方、稳定）
        return await self._fetch_from_github_api(language, since)

    async def _fetch_from_github_api(self, language: str = "", since: str = "daily") -> list[TrendingProject]:
        """
        使用 GitHub Search API 获取热门 AI 项目

        Args:
            language: 编程语言过滤
            since: 时间范围（daily/weekly/monthly）

        Returns:
            list[TrendingProject]: 项目列表
        """
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "HunterAI/2.0"
        }
        if settings.github.token:
            headers["Authorization"] = f"token {settings.github.token}"

        # 根据时间范围设置日期过滤
        from datetime import datetime, timedelta
        if since == "daily":
            date_filter = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        elif since == "weekly":
            date_filter = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        else:  # monthly
            date_filter = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

        # 基于用户关键词构建搜索查询
        base_keyword = self.keyword
        queries = [
            base_keyword,
            f"{base_keyword} tool",
            f"{base_keyword} framework",
            f"{base_keyword} api",
        ]
        # 添加扩展关键词
        if base_keyword in self.KEYWORD_EXPANSION:
            queries.extend(self.KEYWORD_EXPANSION[base_keyword][:3])
        projects = []
        console.print(f"[cyan]🔑 搜索关键词组: {queries[:4]}...[/cyan]")

        for query in queries:
            # 构建搜索 URL
            search_query = f"{query}+pushed:>{date_filter}+stars:>500"
            if language:
                search_query += f"+language:{language}"
            url = f"https://api.github.com/search/repositories?q={search_query}&sort=stars&order=desc&per_page=10"

            try:
                response = await asyncio.to_thread(
                    self.http.get, url, headers=headers
                )

                if response.status_code == 200:
                    items = response.json().get("items", [])
                    for item in items:
                        project = TrendingProject(
                            name=item["full_name"],
                            description=item.get("description", "") or "暂无描述",
                            stars=item["stargazers_count"],
                            forks=item["forks_count"],
                            today_stars=0,  # API 不提供今日新增，后续通过比较计算
                            language=item.get("language", "") or "Unknown",
                            url=item["html_url"],
                            topics=item.get("topics", []),
                        )
                        # 去重
                        if not any(p.name == project.name for p in projects):
                            projects.append(project)
                elif response.status_code == 403:
                    console.print(f"[yellow]⚠️ GitHub API 限流，请配置 token 提高配额[/yellow]")
                    break

                await asyncio.sleep(0.5)  # 避免限流

            except Exception as e:
                console.print(f"[yellow]⚠️ 搜索 '{query}' 失败: {e}[/yellow]")

        # 按 star 数排序
        projects.sort(key=lambda x: x.stars, reverse=True)
        console.print(f"[green]✅ 找到 {len(projects)} 个热门 AI 项目[/green]")
        return projects[:25]  # 返回前 25 个

    def _is_ai_project(self, item: dict) -> bool:
        """判断项目是否为 AI/ML 相关"""
        name = (item.get("name", "") or "").lower()
        desc = (item.get("description", "") or "").lower()
        lang = (item.get("language", "") or "").lower()

        # 检查名称和描述是否包含 AI 关键词
        text = f"{name} {desc}"
        for keyword in self.AI_KEYWORDS:
            if keyword in text:
                return True

        # Python/TypeScript 项目更可能是 AI 相关
        if lang in ["python", "typescript", "jupyter notebook"]:
            # 检查更宽松的关键词
            loose_keywords = ["api", "bot", "chat", "model", "train", "data"]
            for kw in loose_keywords:
                if kw in text:
                    return True

        return False

    async def select_projects(self, projects: list[TrendingProject]) -> tuple[list[TrendingProject], TrendingProject]:
        """
        选择要推荐的项目（自动过滤已推荐过的项目）

        规则：
        - 先过滤掉冷却期内已推荐的项目
        - 2 个项目简介（选 star 增长最快的）
        - 1 个深度解读（选最有特色的）

        Returns:
            (brief_projects, deep_dive_project)
        """
        # 过滤掉冷却期内已推荐的项目 + 向量相似度检查
        filtered_projects = []
        skipped_history = 0  # JSON 历史记录过滤
        skipped_similar = 0  # 向量相似度过滤

        for p in projects:
            # 第一层：检查 JSON 历史记录（精确匹配）
            if self._is_recently_recommended(p.name):
                skipped_history += 1
                console.print(f"[dim]   ⏭️ 跳过已推荐: {p.name}[/dim]")
                continue

            # 第二层：检查 ChromaDB 向量相似度（语义匹配）
            if self._is_similar_in_chromadb(p, threshold=0.85):
                skipped_similar += 1
                console.print(f"[dim]   ⏭️ 跳过相似项目: {p.name}[/dim]")
                continue

            filtered_projects.append(p)

        total_skipped = skipped_history + skipped_similar
        if total_skipped > 0:
            console.print(f"[cyan]🔄 已过滤 {total_skipped} 个项目 (历史记录: {skipped_history}, 语义相似: {skipped_similar})[/cyan]")

        if len(filtered_projects) < 3:
            raise ValueError(f"可选项目数量不足，需要至少 3 个，当前 {len(filtered_projects)} 个（已过滤 {total_skipped} 个重复）")

        # 按今日 star 增长排序
        sorted_by_growth = sorted(filtered_projects, key=lambda x: x.today_stars, reverse=True)

        # 前 2 个作为简介
        brief_projects = sorted_by_growth[:2]

        # 选择深度解读项目（选第 3 个或星数最高但不在简介中的）
        remaining = [p for p in filtered_projects if p not in brief_projects]
        deep_dive_project = remaining[0] if remaining else sorted_by_growth[2]

        console.print(f"[green]📋 已选择项目:[/green]")
        console.print(f"   简介1: {brief_projects[0].name} (⭐{brief_projects[0].stars})")
        console.print(f"   简介2: {brief_projects[1].name} (⭐{brief_projects[1].stars})")
        console.print(f"   深度: {deep_dive_project.name} (⭐{deep_dive_project.stars})")

        return brief_projects, deep_dive_project

    def _generate_project_cover(self, project: TrendingProject, index: int, article_dir: Path = None) -> str:
        """
        为项目生成封面图

        如果配置了 image_model，优先使用 Gemini Imagen 生成 AI 图片
        否则直接使用 socialify 服务生成项目卡片

        Args:
            project: 项目信息
            index: 项目序号（用于文件命名）
            article_dir: 文章目录（如果指定，封面图保存到该目录）

        Returns:
            str: 封面图 URL 或本地路径
        """
        safe_name = project.name.replace("/", "_")  # 文件名安全处理
        cover_filename = f"cover_{index}_{safe_name}.png"

        # 确定输出路径
        if article_dir:
            output_path = get_article_file_path(article_dir, cover_filename)
        else:
            today = get_today_str()
            output_path = get_output_path(f"cover_{safe_name}_{today}.png", "covers")

        # 检查本地文件是否已存在（避免重复生成）
        if output_path.exists():
            console.print(f"   📷 封面图已存在: {project.name}")
            return str(output_path)

        # 检查是否配置了图片生成模型
        if not settings.gemini.has_image_model:
            # 未配置 image_model，直接使用 Socialify 服务
            socialify_url = self._get_socialify_url(project.name)
            console.print(f"   📷 使用 Socialify 卡片: {project.name}")
            return socialify_url

        console.print(f"   🎨 正在为 {project.name} 生成 AI 封面图...")

        try:
            # 尝试使用 Gemini Imagen 生成图片
            response = generate_project_cover(
                project_name=project.name,
                project_desc=project.description,
                output_path=str(output_path),
                style="tech"
            )
            console.print(f"   ✅ AI 封面图已生成: {response.saved_path}")
            return response.saved_path
        except Exception as e:
            console.print(f"   [yellow]⚠️ AI 图片生成失败: {e}[/yellow]")
            # 降级方案：使用 socialify 服务生成美观的项目卡片
            socialify_url = self._get_socialify_url(project.name)
            console.print(f"   📷 使用 Socialify 卡片替代")
            return socialify_url

    def _get_socialify_url(self, project_name: str) -> str:
        """
        获取 Socialify 项目卡片 URL

        Socialify 是一个免费服务，可以为 GitHub 项目生成漂亮的卡片图

        Args:
            project_name: 项目名称（owner/repo 格式）

        Returns:
            str: Socialify 卡片 URL
        """
        # Socialify 服务生成美观的项目卡片
        # 参数说明：
        # - description=1: 显示项目描述
        # - font=Inter: 使用 Inter 字体
        # - language=1: 显示编程语言
        # - name=1: 显示项目名称
        # - owner=1: 显示作者
        # - pattern=Plus: 背景图案
        # - stargazers=1: 显示 Star 数
        # - theme=Auto: 自动主题
        return (
            f"https://socialify.git.ci/{project_name}/image"
            f"?description=1&font=Inter&language=1&name=1&owner=1"
            f"&pattern=Plus&stargazers=1&theme=Auto"
        )

    async def generate_article(
        self,
        brief_projects: list[TrendingProject],
        deep_dive_project: TrendingProject
    ) -> tuple[ArticleContent, Path]:
        """
        使用 AI 生成公众号文章（图文并茂版）

        格式参考微信公众号样板：
        - 开篇问候 + 引言
        - 项目1（带封面图 + emoji 特性列表）
        - 项目2（带封面图 + emoji 特性列表）
        - 项目3 深度解读（带封面图 + 详细分析）
        - 结尾总结 + 推荐阅读

        Returns:
            tuple[ArticleContent, Path]: (文章内容, 文章目录路径)
        """
        console.print("[cyan]🤖 AI 正在生成图文并茂的文章...[/cyan]")

        all_projects = brief_projects + [deep_dive_project]

        # 第一步：构建项目信息（先用 Socialify URL 作为封面占位符）
        projects_info = []
        placeholder_covers = {}  # 用于后续替换
        for i, p in enumerate(brief_projects, 1):
            placeholder_url = self._get_socialify_url(p.name)
            placeholder_covers[p.name] = placeholder_url
            projects_info.append(f"""
## 项目{i}
- 名称: {p.name}
- 描述: {p.description}
- Star: ⭐ {p.stars:,} | 今日新增: +{p.today_stars}
- 语言: {p.language}
- 链接: {p.url}
- 封面图: {placeholder_url}
""")

        deep_placeholder_url = self._get_socialify_url(deep_dive_project.name)
        placeholder_covers[deep_dive_project.name] = deep_placeholder_url
        deep_info = f"""
## 深度解读项目（第3个）
- 名称: {deep_dive_project.name}
- 描述: {deep_dive_project.description}
- Star: ⭐ {deep_dive_project.stars:,} | 今日新增: +{deep_dive_project.today_stars}
- 语言: {deep_dive_project.language}
- 链接: {deep_dive_project.url}
- 封面图: {deep_placeholder_url}
"""

        prompt = f"""
# 任务
你是一位专业的技术公众号编辑，擅长将 GitHub 开源项目转化为**图文并茂**的文章。
请根据以下 3 个 GitHub 项目信息，生成一篇排版精美的「GitHub 开源推荐」公众号文章。

# 参考样板风格
参考文章标题风格：「这 3 个 YYDS 开源 AI 项目，绝了！」
- 标题要有网感，可用数字、口语化表达
- 每个项目配封面图（我会提供图片链接）
- 特性列表用 emoji 图标增强可读性

# 文章结构（严格按此顺序）

## 1. 标题
- 20字以内，吸引眼球但不标题党
- 可以用「这 X 个...」「今日份...」「绝了」等网感表达

## 2. 开篇
- 一句亲切问候（如「家人们好呀~」「宝子们」）
- 简短引言说明今天推荐什么（2-3句，80字内）
- 引导读者点赞/关注（如「觉得有用点个赞呗~」）

## 3. 项目 1 介绍
格式：
```
---
### 1️⃣ 项目名称

![项目封面](封面图URL)

一句话介绍项目是什么、能解决什么问题。

**✨ 核心亮点：**
- 🚀 亮点1（简洁有力）
- 🎯 亮点2
- 💡 亮点3
- 🔥 亮点4

📦 **GitHub:** 项目链接
```

## 4. 项目 2 介绍
格式同上，使用 2️⃣ 编号

## 5. 项目 3 深度解读
格式：
```
---
### 3️⃣ 项目名称（重点推荐 🌟）

![项目封面](封面图URL)

**这个项目我要重点聊聊。** 开头抓住读者注意力。

**🎯 它能做什么：**
详细介绍项目解决的问题和核心价值（150字）

**🛠️ 技术架构：**
- 架构特点1
- 架构特点2
- 架构特点3

**👥 适合人群：**
- 人群1
- 人群2

**📝 快速上手：**
```bash
# 安装命令示例
pip install xxx
```

📦 **GitHub:** 项目链接
```

## 6. 结尾
- 总结今天的推荐（2-3句）
- 引导互动（「你最想尝试哪个？评论区告诉我~」）
- 推荐阅读提示（「喜欢这类内容记得关注哦」）

# 写作风格规范
- 口语化，像朋友聊天，有真实感
- 有观点，敢于说「这个我觉得特别牛」「我最近一直在用」
- **禁止使用**：首先、其次、最后、综上所述、值得注意的是、众所周知
- 关键词用 **粗体** 强调
- 每段 3-5 行，适合手机阅读
- emoji 使用要克制，每个列表项一个即可

# 项目信息
{"".join(projects_info)}

{deep_info}

# 输出要求
1. 直接输出 Markdown 格式，不要任何前缀说明
2. 必须包含每个项目的封面图（使用我提供的路径/URL）
3. 使用 --- 作为项目间的分隔线
4. 代码块使用 ```bash 格式
"""

        try:
            response = self.ai_client.generate_sync(prompt)
            article_text = response.text.strip()

            # 提取标题
            title_match = re.search(r'^#\s*(.+)$', article_text, re.MULTILINE)
            title = title_match.group(1) if title_match else f"今日 GitHub 热门 AI 项目推荐"

            # 第二步：创建文章专属目录（以标题命名）
            console.print(f"[cyan]📁 创建文章目录: {title}[/cyan]")
            article_dir = create_article_dir(title)

            # 第三步：生成封面图到文章目录
            console.print("[cyan]📷 生成项目封面图...[/cyan]")
            cover_paths = {}
            for i, project in enumerate(all_projects, 1):
                cover_paths[project.name] = self._generate_project_cover(project, i, article_dir)

            # 第四步：替换文章中的占位符封面为实际路径
            final_article_text = article_text
            for project_name, placeholder_url in placeholder_covers.items():
                actual_path = cover_paths.get(project_name, placeholder_url)
                # 如果是本地路径，转换为相对路径（便于阅读）
                if actual_path and not actual_path.startswith("http"):
                    # 保留文件名，使用相对路径
                    actual_path = Path(actual_path).name
                final_article_text = final_article_text.replace(placeholder_url, actual_path)

            # 收集所有封面图路径
            cover_image_list = list(cover_paths.values())

            article = ArticleContent(
                title=title,
                intro="",  # 从正文提取
                projects_brief=[
                    {"name": p.name, "url": p.url, "stars": p.stars, "cover": cover_paths[p.name]}
                    for p in brief_projects
                ],
                deep_dive={
                    "name": deep_dive_project.name,
                    "url": deep_dive_project.url,
                    "stars": deep_dive_project.stars,
                    "cover": cover_paths[deep_dive_project.name]
                },
                conclusion="",  # 从正文提取
                full_content=final_article_text,
                cover_images=cover_image_list
            )

            console.print(f"[green]✅ 文章生成成功: {title}[/green]")
            console.print(f"[green]📁 文章目录: {article_dir}[/green]")
            console.print(f"[green]📷 封面图数量: {len(cover_image_list)}[/green]")
            return article, article_dir

        except Exception as e:
            console.print(f"[red]❌ 文章生成失败: {e}[/red]")
            raise

    async def run(self) -> Optional[ArticleContent]:
        """
        执行完整流程

        Returns:
            ArticleContent: 生成的文章内容
        """
        console.print("[bold magenta]🚀 GitHub 开源推荐 启动[/bold magenta]\n")
        console.print(f"[cyan]🔑 初始关键词: {self.keyword}[/cyan]")

        try:
            # 1. 获取 Trending 项目（带自动关键词扩展重试）
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task1 = progress.add_task("[1/4] 采集热门项目...", total=None)

                # 尝试获取项目，如果不足则自动切换关键词
                brief_projects = None
                deep_dive_project = None
                max_retries = 4  # 最多尝试 4 次不同的关键词

                for retry in range(max_retries):
                    self.projects = await self.fetch_trending(since="daily")

                    if len(self.projects) < 3:
                        console.print("[yellow]⚠️ 日榜项目不足，尝试周榜...[/yellow]")
                        self.projects = await self.fetch_trending(since="weekly")

                    progress.update(task1, completed=True)

                    # 2. 选择项目
                    task2 = progress.add_task("[2/4] 选择推荐项目...", total=None)
                    try:
                        brief_projects, deep_dive_project = await self.select_projects(self.projects)
                        progress.update(task2, completed=True)
                        break  # 成功，退出重试循环
                    except ValueError as e:
                        progress.update(task2, completed=True)
                        if "可选项目数量不足" in str(e) and retry < max_retries - 1:
                            # 尝试切换到相近关键词
                            next_keyword = self._get_next_keyword()
                            if next_keyword:
                                console.print(f"[yellow]⚠️ {e}[/yellow]")
                                console.print(f"[cyan]🔄 自动切换关键词: {self.keyword} → {next_keyword}[/cyan]")
                                self.keyword = next_keyword
                                self.tried_keywords.append(next_keyword)
                                task1 = progress.add_task(f"[1/4] 重新采集({next_keyword})...", total=None)
                                continue
                        raise  # 没有更多关键词或其他错误，抛出异常

                if brief_projects is None:
                    raise ValueError("所有关键词都已尝试，仍无法获取足够项目")

                # 3. 生成文章
                task3 = progress.add_task("[3/4] AI 生成文章...", total=None)
                article, article_dir = await self.generate_article(brief_projects, deep_dive_project)
                progress.update(task3, completed=True)

                # 4. 保存并推送
                task4 = progress.add_task("[4/4] 保存并推送...", total=None)
                selected_projects = brief_projects + [deep_dive_project]  # 合并所有推荐的项目
                await self._save_and_push(article, selected_projects, article_dir)
                progress.update(task4, completed=True)

            console.print("\n[bold green]✅ GitHub 开源推荐完成！[/bold green]")
            return article

        except Exception as e:
            console.print(f"[red]❌ 执行失败: {e}[/red]")
            raise

        finally:
            self.http.close()

    def _get_next_keyword(self) -> Optional[str]:
        """
        获取下一个要尝试的关键词

        优先从当前关键词的扩展列表中选择，然后尝试其他常用关键词

        Returns:
            str: 下一个关键词，如果没有则返回 None
        """
        # 1. 先尝试当前关键词的扩展列表
        if self.keyword in self.KEYWORD_EXPANSION:
            for kw in self.KEYWORD_EXPANSION[self.keyword]:
                if kw.lower() not in [k.lower() for k in self.tried_keywords]:
                    return kw

        # 2. 尝试其他常用 AI 关键词
        fallback_keywords = ["llm", "agent", "rag", "automation", "langchain", "ml", "chatbot"]
        for kw in fallback_keywords:
            if kw.lower() not in [k.lower() for k in self.tried_keywords]:
                return kw

        return None

    async def _save_and_push(self, article: ArticleContent, selected_projects: list[TrendingProject], article_dir: Path):
        """
        保存文章并推送到微信

        Args:
            article: 生成的文章内容
            selected_projects: 本次推荐的项目列表（用于记录历史）
            article_dir: 文章保存目录
        """
        # 保存 Markdown 文件到文章目录
        article_path = get_article_file_path(article_dir, "article.md")
        with open(article_path, "w", encoding="utf-8") as f:
            f.write(article.full_content)
        console.print(f"[green]📄 文章已保存: {article_path}[/green]")

        # 保存文章元数据（方便后续查阅）
        metadata = {
            "title": article.title,
            "date": get_today_str(),
            "projects": [
                {"name": p.name, "stars": p.stars, "url": p.url}
                for p in selected_projects
            ],
            "cover_images": article.cover_images,
        }
        metadata_path = get_article_file_path(article_dir, "metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            import json
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        console.print(f"[green]📋 元数据已保存: {metadata_path}[/green]")

        # 保存推荐历史记录（避免下次重复推荐）
        self._save_history(selected_projects)

        # 推送到微信
        if settings.push.enabled:
            success = push_to_wechat(
                title=f"【开源推荐】{article.title}",
                content=article.full_content
            )
            if success:
                console.print("[green]📤 已推送到微信[/green]")
            else:
                console.print("[yellow]⚠️ 微信推送失败[/yellow]")
        else:
            console.print("[dim]📴 微信推送已禁用[/dim]")


async def main():
    """主函数入口"""
    hunter = GitHubTrendingHunter()
    await hunter.run()


if __name__ == "__main__":
    asyncio.run(main())
