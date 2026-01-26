"""
Hunter AI 内容工厂 - GitHub 猎手模块

功能：
- 通过 GitHub API 搜索高星 AI 开源项目
- 使用 Gemini 翻译项目描述为中文
- 本地存储已推荐项目，避免重复推荐
- 生成 MD 报告并推送到微信

使用方法：
    uv run python -m src.intel.github_hunter

GitHub: https://github.com/Pangu-Immortal/hunter-ai-content-factory
Author: Pangu-Immortal
"""

import datetime
import json
import time
from datetime import timedelta

from rich.console import Console
from rich.progress import track

from src.config import ROOT_DIR, settings
from src.intel.utils import (
    create_http_client,
    generate_content_id,
    get_chromadb_client,
    get_dated_output_path,
    get_today_str,
    push_to_wechat,
)
from src.utils.ai_client import get_ai_client

# 终端输出美化
console = Console()

# GitHub 搜索关键词
SEARCH_QUERIES = [
    "DeepSeek tool",
    "LLM Agent framework",
    "RAG pipeline",
    "AI workflow automation",
    "Prompt Engineering tool",
    "Browser Use",
]


class GitHubHunter:
    """GitHub 猎手 - 搜索并分析高星 AI 开源项目（支持去重）"""

    # 共用历史记录文件（与 GitHubTrendingHunter 共享）
    HISTORY_FILE = ROOT_DIR / "data" / "recommended_projects.json"

    # 项目冷却期（天数）
    COOLDOWN_DAYS = 30

    def __init__(self):
        """初始化 GitHub 猎手"""
        self.projects: list[dict] = []  # 本次会话捕获的项目列表
        self.http = create_http_client(timeout=20.0)  # HTTP 客户端
        self._init_ai_client()  # 初始化 AI 客户端
        self._init_chromadb()  # 初始化 ChromaDB
        self.recommended_history: dict = self._load_history()  # 加载历史推荐记录

    def _load_history(self) -> dict:
        """加载已推荐项目历史记录"""
        if self.HISTORY_FILE.exists():
            try:
                with open(self.HISTORY_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                    console.print(f"[dim]📂 已加载 {len(data.get('projects', []))} 条历史推荐记录[/dim]")
                    return data
            except (OSError, json.JSONDecodeError) as e:
                console.print(f"[yellow]⚠️ 历史记录文件损坏: {e}[/yellow]")
        return {"projects": []}

    def _save_history(self) -> None:
        """保存本次推荐的项目到历史记录"""
        if not self.projects:
            return

        today = datetime.datetime.now().strftime("%Y-%m-%d")

        for proj in self.projects:
            project_name = proj["name"]
            existing = next((p for p in self.recommended_history["projects"] if p["name"] == project_name), None)
            if existing:
                existing["recommended_at"] = today
                existing["stars"] = proj["stars"]
            else:
                self.recommended_history["projects"].append(
                    {
                        "name": project_name,
                        "recommended_at": today,
                        "stars": proj["stars"],
                    }
                )

        # 清理 90 天前的旧记录
        cutoff = (datetime.datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        self.recommended_history["projects"] = [
            p for p in self.recommended_history["projects"] if p.get("recommended_at", "2000-01-01") > cutoff
        ]

        self.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.recommended_history, f, ensure_ascii=False, indent=2)
            console.print(f"[green]💾 已保存 {len(self.projects)} 个项目到历史记录[/green]")
        except OSError as e:
            console.print(f"[red]❌ 保存历史记录失败: {e}[/red]")

    def _is_recently_recommended(self, project_name: str) -> bool:
        """检查项目是否在冷却期内被推荐过"""
        cutoff = (datetime.datetime.now() - timedelta(days=self.COOLDOWN_DAYS)).strftime("%Y-%m-%d")
        for record in self.recommended_history.get("projects", []):
            if record.get("name") == project_name:
                if record.get("recommended_at", "2000-01-01") > cutoff:
                    return True
        return False

    def _init_ai_client(self):
        """初始化 AI 客户端"""
        if not settings.gemini.api_key:
            console.print("[red]❌ AI API Key 未配置[/red]")
            raise ValueError("AI API Key 未配置")

        self.ai_client = get_ai_client()  # 获取统一 AI 客户端
        provider = "第三方聚合" if settings.gemini.is_openai_compatible else "官方 Gemini"
        console.print(f"[green]✅ AI 客户端连接成功 ({provider})[/green]")

    def _init_chromadb(self):
        """初始化 ChromaDB 向量数据库"""
        client = get_chromadb_client()
        self.collection = client.get_or_create_collection(name="market_insights")  # 获取或创建集合
        console.print("[green]✅ ChromaDB 数据库连接成功[/green]")

    def translate_summary(self, english_desc: str, project_name: str) -> str:
        """
        使用 Gemini 翻译项目描述为中文

        Args:
            english_desc: 英文项目描述
            project_name: 项目名称

        Returns:
            str: 中文技术简报
        """
        if not english_desc:
            return "暂无描述"

        console.print(f"   🤖 正在翻译: {project_name} ...")

        prompt = f"""
        # Task
        将以下 GitHub 项目的英文描述翻译成**一句话的中文技术简报**。

        # Rules
        1. 拒绝机翻味，使用地道开发者术语 (保留 Agent, RAG 等专有名词)。
        2. 只说核心价值，去除 "Amazing", "Best" 等营销词。
        3. 字数限制：50字以内。

        # Input
        Project: {project_name}
        Description: {english_desc}
        """

        try:
            response = self.ai_client.generate_sync(prompt)  # 使用统一 AI 客户端
            return response.text.strip()
        except Exception as e:
            console.print(f"   [yellow]⚠️ 翻译失败: {e}[/yellow]")
            return english_desc

    def save_to_db(self, project_name: str, desc_cn: str, stars: int, lang: str, url: str, updated_at: str) -> bool:
        """
        保存项目到数据库并加入本次会话缓存

        Args:
            project_name: 项目名称
            desc_cn: 中文描述
            stars: Star 数
            lang: 编程语言
            url: 项目链接
            updated_at: 更新日期

        Returns:
            bool: 是否保存成功
        """
        try:
            content = f"Project: {project_name} | Stars: {stars} | Lang: {lang} | Updated: {updated_at} | Desc: {desc_cn} | Link: {url}"  # 组装内容
            doc_id = generate_content_id("GitHub", content, project_name)  # 生成唯一 ID
            current_time = datetime.datetime.now().isoformat()

            # 存入 ChromaDB
            self.collection.upsert(
                documents=[content],
                metadatas=[{"source": "GitHub", "author": project_name, "tag": "OpenSource", "time": current_time}],
                ids=[doc_id],
            )

            # 加入内存列表
            self.projects.append(
                {"name": project_name, "stars": stars, "lang": lang, "desc": desc_cn, "url": url, "updated": updated_at}
            )

            console.print(f"  💾 已归档: {project_name} (⭐{stars})")
            return True

        except Exception as e:
            console.print(f"  [red]⚠️ 存储失败: {e}[/red]")
            return False

    def hunt(self):
        """执行 GitHub 项目搜索"""
        console.print("[bold cyan]🚀 GitHub 猎手开始狩猎...[/bold cyan]")

        headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "HunterAI/1.0"}

        # 添加 GitHub Token（提高 API 配额）
        if settings.github.token:
            headers["Authorization"] = f"token {settings.github.token}"
            console.print("🔑 GitHub Token 已加载")

        min_stars = settings.github.min_stars  # 最小 Star 数
        days_limit = settings.github.days_since_update  # 更新天数阈值

        for query in track(SEARCH_QUERIES, description="搜索关键词"):
            console.print(f"\n🔍 搜索: {query}")

            api_url = f"https://api.github.com/search/repositories?q={query}+stars:>{min_stars}&sort=updated&order=desc&per_page=3"  # 构建 API URL

            try:
                response = self.http.get(api_url, headers=headers)

                if response.status_code == 200:
                    items = response.json().get("items", [])

                    if not items:
                        console.print("     (无符合条件的项目)")
                        continue

                    for item in items:
                        project_name = item["full_name"]

                        # 检查是否在冷却期内被推荐过
                        if self._is_recently_recommended(project_name):
                            console.print(f"     ⏭️ 跳过已推荐: {project_name}")
                            continue

                        updated_at = item["updated_at"][:10]  # 提取日期
                        last_update = datetime.datetime.strptime(updated_at, "%Y-%m-%d")
                        days_diff = (datetime.datetime.now() - last_update).days

                        if days_diff > days_limit:  # 过滤过期项目
                            continue

                        desc_cn = self.translate_summary(item["description"] or "", item["full_name"])

                        self.save_to_db(
                            project_name=item["full_name"],
                            desc_cn=desc_cn,
                            stars=item["stargazers_count"],
                            lang=item["language"] or "Unknown",
                            url=item["html_url"],
                            updated_at=updated_at,
                        )

                elif response.status_code == 403:
                    console.print("[red]⛔ API 频率超限，请配置 GitHub Token[/red]")
                    break
                else:
                    console.print(f"[yellow]⚠️ API 状态码: {response.status_code}[/yellow]")

                time.sleep(2)  # 避免 API 限流

            except Exception as e:
                console.print(f"[red]❌ 请求异常: {e}[/red]")

    def generate_report(self):
        """生成报告并推送到微信"""
        if not self.projects:
            console.print("[yellow]📭 本次无新项目，跳过报告生成[/yellow]")
            return

        today = get_today_str()
        sorted_projects = sorted(self.projects, key=lambda x: x["stars"], reverse=True)  # 按 Star 数排序

        # 生成 MD 报告内容
        md_content = f"# 🚀 GitHub AI 猎手简报 ({today})\n\n"
        md_content += f"筛选标准: >{settings.github.min_stars} Stars | 共捕获 {len(sorted_projects)} 个项目\n\n"
        md_content += "---\n\n"

        for proj in sorted_projects:
            md_content += f"## [{proj['name']}]({proj['url']})\n\n"
            md_content += (
                f"**⭐ Stars:** {proj['stars']} | **🛠️ 语言:** {proj['lang']} | **📅 更新:** {proj['updated']}\n\n"
            )
            md_content += f"> 📝 {proj['desc']}\n\n"
            md_content += "---\n\n"

        # 保存 MD 报告
        try:
            md_filename = f"GitHub_AI_Report_{today}.md"
            md_filepath = get_dated_output_path(md_filename, "reports")
            with open(md_filepath, "w", encoding="utf-8") as f:
                f.write(md_content)
            console.print(f"\n[green]📄 报告已生成: {md_filepath}[/green]")

        except Exception as e:
            console.print(f"[red]❌ MD 报告生成失败: {e}[/red]")

        # 推送到微信
        push_to_wechat(title=f"【开源猎手】今日捕获 {len(sorted_projects)} 个项目", content=md_content)

        # 保存推荐历史（避免下次重复推荐）
        self._save_history()

    def run(self):
        """运行 GitHub 猎手完整流程"""
        self.hunt()
        self.generate_report()
        self.http.close()


def main():
    """主函数入口"""
    console.print("[bold magenta]🦅 GitHub 猎手 v2.0 启动[/bold magenta]\n")

    try:
        hunter = GitHubHunter()
        hunter.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ 用户中断[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ 运行失败: {e}[/red]")
        raise


if __name__ == "__main__":
    main()
