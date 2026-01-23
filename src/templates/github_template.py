"""
Hunter AI 内容工厂 - GitHub 开源推荐模板

功能：
- 采集 GitHub Trending 上的 AI/ML 热门项目
- 生成「2个项目推荐 + 1个深度解读」格式的文章
- 全自动执行：采集 → 生成 → 推送

使用方法：
    from src.templates import get_template
    template = get_template("github")
    result = await template.run()

GitHub: https://github.com/Pangu-Immortal/hunter-ai-content-factory
Author: Pangu-Immortal
"""

from src.templates import BaseTemplate, TemplateResult, register_template
from src.intel.github_trending import GitHubTrendingHunter
from rich.console import Console

console = Console()


@register_template("github")
class GitHubTemplate(BaseTemplate):
    """
    GitHub 开源推荐模板

    每次生成：
    - 2 个项目简介（各 300 字）
    - 1 个项目深度解读（800 字）
    """

    name = "github"
    description = "GitHub 开源推荐 - 每日热门 AI 项目推荐"
    requires_intel = True

    async def run(self) -> TemplateResult:
        """执行 GitHub 开源推荐流程"""
        self.print_header()

        try:
            # 创建猎手并执行
            hunter = GitHubTrendingHunter()
            article = await hunter.run()

            if article:
                return TemplateResult(
                    success=True,
                    title=article.title,
                    content=article.full_content,
                    output_path=str(article.full_content[:50]) + "...",  # 简化显示
                    push_status="已推送" if article else "未推送",
                )
            else:
                return TemplateResult(
                    success=False,
                    title="",
                    content="",
                    output_path="",
                    push_status="失败",
                    error="文章生成失败",
                )

        except Exception as e:
            console.print(f"[red]❌ GitHub 模板执行失败: {e}[/red]")
            return TemplateResult(
                success=False,
                title="",
                content="",
                output_path="",
                push_status="失败",
                error=str(e),
            )
