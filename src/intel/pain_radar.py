"""
Hunter AI 内容工厂 - 痛点雷达模块

功能：
- 扫描 Twitter + Reddit 上关于 AI 产品的用户抱怨
- 使用 Gemini 进行痛点诊断分析
- 所有痛点存入 SQLite 数据库（支持标签、合并）
- 生成 MD 诊断报告并存入数据库
- 推送到微信

使用方法：
    uv run python -m src.intel.pain_radar

GitHub: https://github.com/Pangu-Immortal/hunter-ai-content-factory
Author: Pangu-Immortal
"""

import asyncio
import datetime
import random
import time

from rich.console import Console
from twikit import Client as TwitterClient

from src.config import settings
from src.intel.pain_store import PainStore  # 痛点结构化存储
from src.intel.utils import (
    generate_content_id,
    get_chromadb_client,
    get_output_path,
    get_today_str,
    push_to_wechat,
)
from src.utils.ai_client import get_ai_client

# 终端输出美化
console = Console()

# 目标产品列表
TARGETS = ["DeepSeek", "ChatGPT", "Claude", "Gemini", "Cursor", "Windsurf"]

# 痛点关键词
PAIN_KEYWORDS = ["error", "fail", "broken", "slow", "stupid", "bug", "api down", "not working"]


class PainRadar:
    """痛点雷达 - 扫描 AI 产品用户抱怨"""

    def __init__(self):
        """初始化痛点雷达"""
        self.pain_points: list[dict] = []  # 本次会话捕获的痛点列表（包含元数据）
        self._init_ai_client()  # 初始化 AI 客户端
        self._init_pain_store()  # 初始化痛点结构化存储
        self._init_chromadb()  # 初始化 ChromaDB（向量去重）

    def _init_ai_client(self):
        """初始化 AI 客户端"""
        if not settings.gemini.api_key:
            console.print("[red]❌ AI API Key 未配置[/red]")
            raise ValueError("AI API Key 未配置")

        self.ai_client = get_ai_client()
        provider = "第三方聚合" if settings.gemini.is_openai_compatible else "官方 Gemini"
        console.print(f"[green]✅ AI 客户端连接成功 ({provider})[/green]")

    def _init_pain_store(self):
        """初始化痛点结构化存储（SQLite）"""
        self.pain_store = PainStore()

    def _init_chromadb(self):
        """初始化 ChromaDB"""
        client = get_chromadb_client()
        self.collection = client.get_or_create_collection(name="user_pain_points")
        console.print("[green]✅ ChromaDB 数据库连接成功[/green]")

    def save_pain(self, source: str, author: str, content: str, url: str = None) -> bool:
        """
        保存痛点到数据库

        同时存储到：
        1. SQLite 结构化数据库（支持标签、分类、合并）
        2. ChromaDB 向量数据库（用于语义去重）

        Args:
            source: 来源平台
            author: 作者
            content: 内容
            url: 原始链接

        Returns:
            bool: 是否保存成功
        """
        try:
            # 1. 存储到 SQLite 结构化数据库（自动推断标签、检测相似、合并）
            pain, is_new = self.pain_store.add_pain(
                content=content,
                source=source,
                author=author,
                original_url=url,
                auto_merge=True,  # 自动合并相似痛点
            )

            # 2. 同时存储到 ChromaDB（保持向量索引）
            current_time = datetime.datetime.now().isoformat()
            doc_id = generate_content_id("PAIN", content, author)

            self.collection.upsert(
                documents=[content],
                metadatas=[
                    {
                        "source": source,
                        "author": str(author),
                        "type": "pain",
                        "time": current_time,
                        "platform": pain.platform or "",
                        "category": pain.category or "",
                    }
                ],
                ids=[doc_id],
            )

            # 记录到本次会话列表（包含结构化数据）
            self.pain_points.append(
                {
                    "id": pain.id,
                    "content": content,
                    "source": source,
                    "author": author,
                    "platform": pain.platform,
                    "category": pain.category,
                    "severity": pain.severity,
                    "tags": pain.tags,
                    "frequency": pain.frequency,
                    "is_new": is_new,
                }
            )

            status = "新增" if is_new else f"合并(频率:{pain.frequency})"
            console.print(f"  🩸 捕获痛点 [{status}]: {content[:40]}...")
            return True

        except Exception as e:
            console.print(f"  [red]⚠️ 存储失败: {e}[/red]")
            return False

    async def scan_twitter(self) -> int:
        """
        扫描 Twitter 上的用户抱怨

        Returns:
            int: 捕获的痛点数量
        """
        console.print("\n[bold cyan]🐦 正在扫描 Twitter 最新愤怒值...[/bold cyan]")
        client = TwitterClient(language="en-US")
        count = 0

        # 生成搜索词组合
        search_queries = []
        for target in TARGETS:
            for pain in PAIN_KEYWORDS:
                search_queries.append(f'"{target}" {pain}')

        # 随机选择 5 个搜索词
        selected_queries = random.sample(search_queries, min(5, len(search_queries)))
        console.print(f"🎯 本次搜索词: {selected_queries}")

        # 加载 Twitter Cookies
        cookies_file = settings.twitter.cookies_file
        if not cookies_file.exists():
            console.print(f"[red]❌ Twitter Cookies 文件不存在: {cookies_file}[/red]")
            return 0

        try:
            # 加载并转换 cookies 格式
            # Cookie-Editor 导出格式: [{name, value, ...}, ...]
            # twikit 2.x 期望格式: {name: value, ...}
            import json

            with open(cookies_file, encoding="utf-8") as f:
                cookies_data = json.load(f)

            # 检查格式并转换
            if isinstance(cookies_data, list):
                # Cookie-Editor 数组格式 → 字典格式
                cookies_dict = {c["name"]: c["value"] for c in cookies_data if "name" in c and "value" in c}
                console.print(f"[dim]🔄 已转换 {len(cookies_dict)} 个 cookies 为 twikit 格式[/dim]")
                client.set_cookies(cookies_dict)
            elif isinstance(cookies_data, dict):
                # 已经是字典格式，直接使用
                client.set_cookies(cookies_data)
            else:
                raise ValueError(f"不支持的 cookies 格式: {type(cookies_data)}")

            for query in selected_queries:
                console.print(f"  🔍 搜索: {query}")

                try:
                    tweets = await client.search_tweet(query, product="Latest", count=3)

                    if not tweets:
                        console.print("     (无结果)")
                        continue

                    for tweet in tweets:
                        text = tweet.text.replace("\n", " ")
                        user = tweet.user.name if tweet.user else "Unknown"
                        url = f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}" if tweet.user else None
                        if self.save_pain("Twitter", user, text, url):
                            count += 1

                    await asyncio.sleep(2)  # 避免限流

                except Exception as e:
                    console.print(f"     [yellow]⚠️ 搜索出错: {e}[/yellow]")

        except Exception as e:
            console.print(f"[red]❌ Twitter 登录失败: {e}[/red]")

        return count

    async def scan_reddit(self) -> int:
        """
        扫描 Reddit 上的用户痛点

        Returns:
            int: 捕获的痛点数量
        """
        console.print("\n[bold cyan]🔴 正在扫描 Reddit 用户痛点...[/bold cyan]")
        count = 0

        try:
            from src.intel.reddit_hunter import RedditHunter

            hunter = RedditHunter(mode="pain")
            await hunter.run()

            # 将 Reddit 痛点保存到数据库
            for pain_data in hunter.get_pain_points():
                content = pain_data.get("content", "")
                author = pain_data.get("author", "Reddit User")
                url = pain_data.get("url", "")
                subreddit = pain_data.get("subreddit", "")

                if self.save_pain(f"Reddit/r/{subreddit}", author, content, url):
                    count += 1

            console.print(f"[green]✅ Reddit 采集完成: {count} 条痛点[/green]")

        except ImportError as e:
            console.print(f"[yellow]⚠️ Reddit 模块不可用: {e}[/yellow]")

        except Exception as e:
            console.print(f"[red]❌ Reddit 采集失败: {e}[/red]")

        return count

    def analyze_pain_points(self, raw_data: str) -> str:
        """
        使用 Gemini 分析痛点

        Args:
            raw_data: 原始痛点数据

        Returns:
            str: 分析报告
        """
        console.print("\n[bold cyan]👨‍⚕️ AI 正在诊断痛点...[/bold cyan]")

        prompt = f"""
        # Role: AI Ecosystem Pathologist (AI 生态病理学家)
        # Specialization: 擅长从混乱的用户抱怨中，解剖出大模型的底层缺陷，并构建工程级解决方案。

        # Workflow (诊断流程)
        ## Step 1: 噪音提纯 (Triage)
        分析以下数据，过滤情绪发泄，提炼出 **Top 3 阻断性痛点 (Blockers)**。

        ## Step 2: 深度尸检 (Technical Autopsy)
        针对 Top 1 痛点，进行技术层面的根因分析。使用 LLM 原理术语 (如 Context Window Drift, Hallucination via Logic Gap)。

        ## Step 3: 基因编辑 (The Engineering Cure)
        编写一个 **System Prompt** 来规避此缺陷。必须包含：防御性思维、结构化输出、思维链 (CoT)。

        ## Step 4: 生态位嗅探 (The Gap Analysis)
        推演一个 Micro-SaaS 产品形态。

        # Raw User Data
        {raw_data}
        """

        max_retries = 5
        wait_time = 5

        for attempt in range(max_retries):
            try:
                response = self.ai_client.generate_sync(prompt)
                return response.text

            except Exception as e:
                console.print(f"[yellow]⚠️ 诊断尝试 {attempt + 1}/{max_retries} 失败: {e}[/yellow]")
                if attempt < max_retries - 1:
                    console.print(f"⏳ 等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    wait_time += 5
                else:
                    console.print("[red]❌ 重试耗尽，放弃治疗[/red]")

        return "❌ 诊断失败: 网络或API错误"

    def deliver_report(self, content: str):
        """
        生成报告并推送

        Args:
            content: 报告内容
        """
        if content.startswith("❌"):
            console.print(f"\n[red]🚫 任务终止: {content}[/red]")
            return

        today = get_today_str()

        # 保存 MD 报告到文件
        try:
            md_filename = f"Pain_Report_{today}.md"
            md_filepath = get_output_path(md_filename, "reports")
            md_content = f"# 💊 AI 痛点诊断报告 ({today})\n\n{content}"
            with open(md_filepath, "w", encoding="utf-8") as f:
                f.write(md_content)
            console.print(f"[green]📝 MD 报告已保存: {md_filepath}[/green]")

            # 将报告内容存入数据库（ChromaDB）
            self._save_report_to_db(today, md_content)

        except Exception as e:
            console.print(f"[yellow]⚠️ MD 报告保存失败: {e}[/yellow]")

        # 推送到微信
        wechat_body = f"# 💊 AI 痛点诊断报告 ({today})\n\n{content}"
        push_to_wechat(title="【痛点雷达】诊断报告", content=wechat_body)

    def _save_report_to_db(self, date: str, content: str):
        """
        将报告保存到 ChromaDB 数据库

        Args:
            date: 报告日期
            content: 报告内容
        """
        try:
            report_id = f"pain_report_{date}"
            self.collection.upsert(
                documents=[content],
                metadatas=[
                    {
                        "type": "pain_report",
                        "date": date,
                        "source": "pain_radar",
                        "time": datetime.datetime.now().isoformat(),
                    }
                ],
                ids=[report_id],
            )
            console.print("[green]💾 报告已存入数据库[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠️ 数据库存储失败: {e}[/yellow]")

    async def run(self):
        """运行痛点雷达完整流程（Twitter + Reddit）"""
        # 并行扫描 Twitter 和 Reddit
        twitter_count = await self.scan_twitter()
        reddit_count = await self.scan_reddit()

        total_count = twitter_count + reddit_count
        console.print(f"\n📊 共捕获 {total_count} 个痛点 (Twitter: {twitter_count}, Reddit: {reddit_count})")

        # 打印数据库统计
        self.pain_store.print_stats()

        if total_count > 0:
            # 格式化痛点数据用于 AI 分析
            raw_pain = self._format_pains_for_analysis()
            report = self.analyze_pain_points(raw_pain)
            self.deliver_report(report)

            # 更新 AI 分析结果到数据库
            self._update_ai_analysis(report)
        else:
            console.print("[yellow]🤷‍♂️ 未捕获到痛点，流程结束[/yellow]")

        # 关闭数据库连接
        self.pain_store.close()

    def _format_pains_for_analysis(self) -> str:
        """格式化痛点数据供 AI 分析"""
        lines = []
        for i, pain in enumerate(self.pain_points, 1):
            platform = pain.get("platform", "Unknown")
            category = pain.get("category", "Unknown")
            tags = ", ".join(pain.get("tags", [])[:3])
            content = pain.get("content", "")
            lines.append(f"{i}. [{platform}][{category}] {content}")
            if tags:
                lines.append(f"   标签: {tags}")
        return "\n".join(lines)

    def _update_ai_analysis(self, report: str):
        """将 AI 分析结果更新到数据库"""
        # 为本次捕获的所有痛点更新分析摘要
        for pain in self.pain_points:
            if pain.get("is_new"):  # 只更新新增的痛点
                self.pain_store.update_ai_analysis(pain_id=pain["id"], analysis=f"报告日期: {get_today_str()}")


async def main():
    """主函数入口"""
    console.print("[bold magenta]📡 痛点雷达 v3.0 启动 (Twitter + Reddit)[/bold magenta]\n")

    try:
        radar = PainRadar()
        await radar.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ 用户中断[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ 运行失败: {e}[/red]")
        raise


if __name__ == "__main__":
    asyncio.run(main())
