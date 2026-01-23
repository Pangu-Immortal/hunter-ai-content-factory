"""
Hunter AI 内容工厂 - Reddit 采集模块

功能：
- 采集 Reddit AI 相关 subreddit 的热门帖子
- 提取用户讨论、痛点、技术趋势
- 支持多个子版块并行采集
- 去重并存入数据库

使用方法：
    from src.intel.reddit_hunter import RedditHunter
    hunter = RedditHunter()
    posts = await hunter.run()

GitHub: https://github.com/Pangu-Immortal/hunter-ai-content-factory
Author: Pangu-Immortal
"""

import asyncio
import datetime
from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console
from rich.progress import track

from src.config import settings
from src.intel.utils import (
    create_http_client,
    get_chromadb_client,
    generate_content_id,
    get_today_str,
)

# 终端输出美化
console = Console()


@dataclass
class RedditPost:
    """Reddit 帖子数据结构"""
    id: str                      # 帖子 ID
    title: str                   # 标题
    selftext: str                # 正文（self post）
    author: str                  # 作者
    subreddit: str               # 子版块
    score: int                   # 分数（upvotes - downvotes）
    num_comments: int            # 评论数
    url: str                     # 帖子链接
    permalink: str               # Reddit 永久链接
    created_utc: float           # 创建时间戳
    is_self: bool = True         # 是否为文字帖
    link_flair_text: str = ""    # 帖子标签
    thumbnail: str = ""          # 缩略图 URL（封面图）
    top_comments: list[dict] = field(default_factory=list)  # 热门评论


class RedditHunter:
    """
    Reddit 猎手

    采集 AI/ML 相关 subreddit 的热门帖子和讨论。
    支持多个子版块并行采集，自动去重。
    """

    # AI 相关的 Subreddit 列表
    AI_SUBREDDITS = [
        "MachineLearning",       # 机器学习学术讨论
        "artificial",            # AI 综合讨论
        "LocalLLaMA",            # 本地大模型
        "ChatGPT",               # ChatGPT 使用讨论
        "ClaudeAI",              # Claude AI 讨论
        "singularity",           # AI 未来/通用智能
        "StableDiffusion",       # 图像生成
        "midjourney",            # Midjourney 讨论
        "learnmachinelearning",  # ML 学习
        "PromptEngineering",     # 提示词工程
    ]

    # 痛点相关的 Subreddit 列表
    PAIN_SUBREDDITS = [
        "ChatGPT",               # ChatGPT 问题反馈
        "ClaudeAI",              # Claude 问题反馈
        "LocalLLaMA",            # 本地模型问题
        "StableDiffusion",       # SD 问题
        "midjourney",            # MJ 问题
        "artificial",            # AI 综合问题
    ]

    # 痛点关键词
    PAIN_KEYWORDS = [
        "bug", "error", "broken", "issue", "problem", "fail",
        "slow", "crash", "stuck", "not working", "hate",
        "frustrating", "annoying", "worse", "downgrade",
        "help", "can't", "won't", "doesn't work"
    ]

    # 最低分数阈值
    MIN_SCORE = 10

    def __init__(self, mode: str = "trending"):
        """
        初始化 Reddit 猎手

        Args:
            mode: 采集模式
                - "trending": 采集热门趋势
                - "pain": 采集用户痛点
        """
        self.mode = mode
        self.http = create_http_client(timeout=30.0)
        self.http.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) HunterAI/2.0"
        })
        self.posts: list[RedditPost] = []
        self._init_chromadb()

    def _init_chromadb(self):
        """初始化 ChromaDB（向量去重）"""
        try:
            client = get_chromadb_client()
            self.collection = client.get_or_create_collection(
                name="reddit_posts",
                metadata={"description": "Reddit 帖子存储，用于去重"}
            )
            console.print(f"[green]✅ ChromaDB 连接成功 (Reddit 集合)[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠️ ChromaDB 初始化失败: {e}[/yellow]")
            self.collection = None

    def _is_duplicate(self, post_id: str) -> bool:
        """检查帖子是否已存在"""
        if self.collection is None:
            return False

        try:
            existing = self.collection.get(ids=[post_id])
            return bool(existing and existing["ids"])
        except Exception:
            return False

    def _save_post(self, post: RedditPost) -> bool:
        """
        保存帖子到数据库

        Args:
            post: Reddit 帖子

        Returns:
            bool: 是否为新帖子
        """
        if self.collection is None:
            return True  # 无数据库时视为新帖子

        post_id = f"reddit_{post.id}"

        if self._is_duplicate(post_id):
            console.print(f"[dim]   ⏭️ 跳过已采集: {post.title[:30]}...[/dim]")
            return False

        try:
            doc_text = f"{post.title} {post.selftext[:500]}"

            self.collection.upsert(
                documents=[doc_text],
                metadatas=[{
                    "subreddit": post.subreddit,
                    "author": post.author,
                    "score": post.score,
                    "url": post.url,
                    "collected_at": datetime.datetime.now().isoformat(),
                }],
                ids=[post_id]
            )

            console.print(f"[green]   💾 新帖子: {post.title[:40]}... (r/{post.subreddit})[/green]")
            return True

        except Exception as e:
            console.print(f"[yellow]   ⚠️ 存储失败: {e}[/yellow]")
            return True  # 存储失败也视为新帖子

    async def fetch_subreddit(
        self,
        subreddit: str,
        sort: str = "hot",
        limit: int = 10
    ) -> list[RedditPost]:
        """
        获取指定 subreddit 的帖子

        Args:
            subreddit: 子版块名称
            sort: 排序方式（hot/new/top/rising）
            limit: 获取数量

        Returns:
            list[RedditPost]: 帖子列表
        """
        url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"
        posts = []

        try:
            response = await asyncio.to_thread(self.http.get, url)

            if response.status_code == 200:
                data = response.json()
                children = data.get("data", {}).get("children", [])

                for child in children:
                    post_data = child.get("data", {})

                    # 过滤低分帖子
                    if post_data.get("score", 0) < self.MIN_SCORE:
                        continue

                    # 过滤置顶帖子
                    if post_data.get("stickied", False):
                        continue

                    # 获取缩略图（过滤无效值）
                    thumbnail = post_data.get("thumbnail", "")
                    if thumbnail in ["self", "default", "nsfw", "spoiler", ""]:
                        thumbnail = ""  # 无有效缩略图

                    post = RedditPost(
                        id=post_data.get("id", ""),
                        title=post_data.get("title", ""),
                        selftext=post_data.get("selftext", "") or "",
                        author=post_data.get("author", "[deleted]"),
                        subreddit=post_data.get("subreddit", subreddit),
                        score=post_data.get("score", 0),
                        num_comments=post_data.get("num_comments", 0),
                        url=post_data.get("url", ""),
                        permalink=f"https://reddit.com{post_data.get('permalink', '')}",
                        created_utc=post_data.get("created_utc", 0),
                        is_self=post_data.get("is_self", True),
                        link_flair_text=post_data.get("link_flair_text", "") or "",
                        thumbnail=thumbnail,
                    )

                    posts.append(post)

            elif response.status_code == 429:
                console.print(f"[yellow]⚠️ Reddit 限流，等待重试...[/yellow]")
                await asyncio.sleep(5)

            else:
                console.print(f"[yellow]⚠️ r/{subreddit} 获取失败: {response.status_code}[/yellow]")

        except Exception as e:
            console.print(f"[red]❌ r/{subreddit} 采集异常: {e}[/red]")

        return posts

    async def fetch_post_comments(self, post: RedditPost, limit: int = 5) -> list[dict]:
        """
        获取帖子的热门评论

        Args:
            post: 帖子对象
            limit: 评论数量

        Returns:
            list[dict]: 评论列表
        """
        url = f"https://www.reddit.com/r/{post.subreddit}/comments/{post.id}.json?limit={limit}"
        comments = []

        try:
            response = await asyncio.to_thread(self.http.get, url)

            if response.status_code == 200:
                data = response.json()

                # Reddit 评论 API 返回数组，第二个元素是评论
                if len(data) >= 2:
                    comment_data = data[1].get("data", {}).get("children", [])

                    for child in comment_data[:limit]:
                        if child.get("kind") != "t1":  # t1 表示评论
                            continue

                        c_data = child.get("data", {})
                        comments.append({
                            "author": c_data.get("author", "[deleted]"),
                            "body": c_data.get("body", ""),
                            "score": c_data.get("score", 0),
                        })

        except Exception as e:
            console.print(f"[dim]   评论获取失败: {e}[/dim]")

        return comments

    def _contains_pain_keyword(self, text: str) -> bool:
        """检查文本是否包含痛点关键词"""
        text_lower = text.lower()
        return any(kw in text_lower for kw in self.PAIN_KEYWORDS)

    async def scan_trending(self) -> int:
        """
        扫描热门趋势

        Returns:
            int: 采集数量
        """
        console.print("\n[bold cyan]🔥 扫描 Reddit AI 热门趋势...[/bold cyan]")
        count = 0

        for subreddit in self.AI_SUBREDDITS:
            console.print(f"\n  📱 r/{subreddit}")

            posts = await self.fetch_subreddit(subreddit, sort="hot", limit=5)

            for post in posts:
                if self._save_post(post):
                    self.posts.append(post)
                    count += 1

            await asyncio.sleep(1)  # 避免限流

        return count

    async def scan_pain_points(self) -> int:
        """
        扫描用户痛点

        Returns:
            int: 采集数量
        """
        console.print("\n[bold cyan]🩸 扫描 Reddit 用户痛点...[/bold cyan]")
        count = 0

        for subreddit in self.PAIN_SUBREDDITS:
            console.print(f"\n  📱 r/{subreddit}")

            # 获取最新帖子（痛点通常出现在新帖子中）
            posts = await self.fetch_subreddit(subreddit, sort="new", limit=15)

            for post in posts:
                # 检查是否包含痛点关键词
                text = f"{post.title} {post.selftext}"
                if not self._contains_pain_keyword(text):
                    continue

                if self._save_post(post):
                    # 获取热门评论（可能包含解决方案）
                    post.top_comments = await self.fetch_post_comments(post, limit=3)
                    self.posts.append(post)
                    count += 1

            await asyncio.sleep(1)

        return count

    def format_posts_for_ai(self) -> str:
        """
        格式化帖子数据供 AI 分析

        Returns:
            str: 格式化的文本
        """
        lines = []

        for i, post in enumerate(self.posts, 1):
            lines.append(f"## 帖子 {i}")
            lines.append(f"- 标题: {post.title}")
            lines.append(f"- 子版块: r/{post.subreddit}")
            lines.append(f"- 分数: {post.score} | 评论: {post.num_comments}")
            lines.append(f"- 链接: {post.permalink}")

            if post.selftext:
                content = post.selftext[:300]
                if len(post.selftext) > 300:
                    content += "..."
                lines.append(f"- 内容: {content}")

            if post.top_comments:
                lines.append("- 热门评论:")
                for c in post.top_comments[:3]:
                    lines.append(f"  - @{c['author']}: {c['body'][:100]}...")

            lines.append("")

        return "\n".join(lines)

    def get_pain_points(self) -> list[dict]:
        """
        获取结构化的痛点数据

        Returns:
            list[dict]: 痛点列表
        """
        return [
            {
                "source": "Reddit",
                "subreddit": post.subreddit,
                "content": f"{post.title}\n{post.selftext[:200]}",
                "author": post.author,
                "url": post.permalink,
                "score": post.score,
                "comments": post.top_comments,
            }
            for post in self.posts
        ]

    async def run(self, subreddits: list[str] = None) -> list[RedditPost]:
        """
        执行采集流程

        Args:
            subreddits: 指定要采集的子版块列表（可选）

        Returns:
            list[RedditPost]: 采集到的帖子
        """
        console.print(f"[bold magenta]🎯 Reddit 猎手启动 (模式: {self.mode})[/bold magenta]\n")

        try:
            if self.mode == "pain":
                count = await self.scan_pain_points()
            else:
                count = await self.scan_trending()

            console.print(f"\n[green]📊 共采集 {count} 条 Reddit 内容[/green]")
            return self.posts

        except Exception as e:
            console.print(f"[red]❌ Reddit 采集失败: {e}[/red]")
            raise

        finally:
            self.http.close()


async def main():
    """主函数入口"""
    # 测试热门趋势采集
    hunter = RedditHunter(mode="trending")
    posts = await hunter.run()

    if posts:
        console.print("\n[cyan]📝 采集结果预览:[/cyan]")
        for post in posts[:5]:
            console.print(f"  - [{post.score}⬆] {post.title[:50]}...")


if __name__ == "__main__":
    asyncio.run(main())
