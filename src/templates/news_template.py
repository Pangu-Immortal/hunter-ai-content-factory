"""
Hunter AI 内容工厂 - 资讯快报模板

功能：
- 汇总 HackerNews 和 Twitter 热点
- 生成每日 AI 资讯快报
- 全自动执行：采集 → 筛选 → 生成 → 推送

使用方法：
    from src.templates import get_template
    template = get_template("news")
    result = await template.run()

GitHub: https://github.com/Pangu-Immortal/hunter-ai-content-factory
Author: Pangu-Immortal
"""

from src.templates import BaseTemplate, TemplateResult, register_template
from src.intel.utils import get_output_path, get_today_str, push_to_wechat
from src.config import settings
from rich.console import Console

console = Console()


@register_template("news")
class NewsTemplate(BaseTemplate):
    """
    资讯快报模板

    流程：
    1. 从 HackerNews + Twitter 采集热点
    2. AI 筛选和分类
    3. 生成资讯快报文章
    """

    name = "news"
    description = "资讯快报 - AI 行业每日热点速递"
    requires_intel = True

    async def run(self) -> TemplateResult:
        """执行资讯快报流程"""
        self.print_header()

        try:
            # 导入全能猎手
            from src.intel.auto_publisher import AutoPublisher

            # 运行全能猎手
            console.print("[cyan]📰 启动资讯采集...[/cyan]")
            publisher = AutoPublisher()
            await publisher.run()

            # 检查是否有结果
            if publisher.article_content:
                today = get_today_str()
                title = publisher.article_title or f"【AI 资讯】{today} 热点速递"
                content = publisher.article_content

                # 保存文章
                output_path = get_output_path(f"news_{today}.md", "articles")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(f"# {title}\n\n{content}")

                return TemplateResult(
                    success=True,
                    title=title,
                    content=content,
                    output_path=str(output_path),
                    push_status=publisher.push_status or "已推送",
                )
            else:
                return TemplateResult(
                    success=False,
                    title="",
                    content="",
                    output_path="",
                    push_status="失败",
                    error="未采集到资讯数据",
                )

        except ImportError as e:
            console.print(f"[yellow]⚠️ 全能猎手模块不可用: {e}[/yellow]")
            return TemplateResult(
                success=False,
                title="",
                content="",
                output_path="",
                push_status="失败",
                error=f"模块导入失败: {e}",
            )

        except Exception as e:
            console.print(f"[red]❌ 资讯模板执行失败: {e}[/red]")
            return TemplateResult(
                success=False,
                title="",
                content="",
                output_path="",
                push_status="失败",
                error=str(e),
            )
