"""
Hunter AI 内容工厂 - 小红书内容模板

功能：
- 采集小红书热门内容
- 生成种草推荐/测评对比/攻略指南类文章
- 全自动执行：采集 → 分析 → 生成 → 推送
- 双采集引擎：Playwright（主） + httpx API（备）

使用方法：
    from src.templates import get_template
    template = get_template("xhs")
    result = await template.run()

GitHub: https://github.com/Pangu-Immortal/hunter-ai-content-factory
Author: Pangu-Immortal
"""

from rich.console import Console

from src.config import settings
from src.templates import BaseTemplate, TemplateResult, register_template

console = Console()


@register_template("xhs")
class XiaohongshuTemplate(BaseTemplate):
    """
    小红书内容模板

    流程：
    1. 通过 Playwright 采集小红书热门笔记（主方案）
    2. 若 Playwright 失败，自动切换 httpx API 方案（备选）
    3. AI 分析提炼核心内容
    4. 生成公众号风格文章
    5. 推送到微信
    """

    name = "xhs"
    description = "小红书热门 - 采集热门笔记生成种草文章"
    requires_intel = True

    def __init__(self, keyword: str = "AI 工具", count: int = 10):
        """
        初始化模板

        Args:
            keyword: 搜索关键词
            count: 采集数量
        """
        super().__init__()
        self.keyword = keyword
        self.count = count

    async def _run_playwright(self) -> dict:
        """
        方案一：Playwright 浏览器采集（推荐）

        优点：绕过签名验证，稳定性高
        """
        from src.intel.xiaohongshu_browser import XiaohongshuBrowser

        console.print("[cyan]📱 方案一：Playwright 浏览器采集[/cyan]")
        hunter = XiaohongshuBrowser()

        if not hunter.is_logged_in():
            return {
                "success": False,
                "error": "未配置 Cookie",
            }

        return await hunter.run(keyword=self.keyword, count=self.count)

    async def _run_httpx_api(self) -> dict:
        """
        方案二：httpx API 直连（备选）

        注意：可能触发签名验证失败
        """
        from src.intel.xiaohongshu_hunter import XiaohongshuHunter

        console.print("[cyan]📱 方案二：httpx API 采集[/cyan]")
        hunter = XiaohongshuHunter()

        if not hunter.is_logged_in():
            return {
                "success": False,
                "error": "未配置 Cookie",
            }

        return await hunter.run(keyword=self.keyword, count=self.count)

    async def run(self) -> TemplateResult:
        """
        执行小红书内容采集流程

        自动切换机制：
        1. 优先使用 Playwright 浏览器采集
        2. 若失败，自动切换 httpx API 方案
        """
        self.print_header()

        # 检查 Cookie 配置
        if not hasattr(settings, "xiaohongshu") or not settings.xiaohongshu.cookies:
            console.print("[yellow]⚠️ 未配置小红书 Cookie[/yellow]")
            console.print("[cyan]   请在 config.yaml 中配置 xiaohongshu.cookies[/cyan]")
            console.print("[dim]   获取方法: 浏览器登录小红书 → F12 → Console → 输入 document.cookie[/dim]")
            return TemplateResult(
                success=False,
                title="",
                content="",
                output_path="",
                push_status="失败",
                error="未配置小红书 Cookie，请在 config.yaml 中配置 xiaohongshu.cookies",
            )

        result = None
        last_error = ""

        # ═══════════════════════════════════════════════════════════════════════
        # 方案一：Playwright 浏览器采集（主方案）
        # ═══════════════════════════════════════════════════════════════════════
        try:
            console.print(f"[bold cyan]🚀 启动小红书采集: {self.keyword}[/bold cyan]")
            result = await self._run_playwright()

            if result.get("success"):
                console.print("[green]✅ Playwright 采集成功[/green]")
                return TemplateResult(
                    success=True,
                    title=result.get("article_title", ""),
                    content=result.get("article_content", ""),
                    output_path=result.get("output_path", ""),
                    push_status="已推送" if settings.push.enabled else "未推送",
                )
            else:
                last_error = result.get("error", "Playwright 采集失败")
                console.print(f"[yellow]⚠️ Playwright 采集失败: {last_error}[/yellow]")

        except ImportError as e:
            last_error = f"Playwright 未安装: {e}"
            console.print(f"[yellow]⚠️ {last_error}[/yellow]")
            console.print("[dim]   安装命令: uv sync && uv run playwright install chromium[/dim]")

        except Exception as e:
            last_error = f"Playwright 异常: {e}"
            console.print(f"[yellow]⚠️ {last_error}[/yellow]")

        # ═══════════════════════════════════════════════════════════════════════
        # 方案二：httpx API 采集（备选方案）
        # ═══════════════════════════════════════════════════════════════════════
        console.print("[cyan]🔄 自动切换备选方案...[/cyan]")

        try:
            result = await self._run_httpx_api()

            if result.get("success"):
                console.print("[green]✅ httpx API 采集成功[/green]")
                return TemplateResult(
                    success=True,
                    title=result.get("article_title", ""),
                    content=result.get("article_content", ""),
                    output_path=result.get("output_path", ""),
                    push_status="已推送" if settings.push.enabled else "未推送",
                )
            else:
                last_error = result.get("error", "httpx API 采集失败")
                console.print(f"[red]❌ httpx API 采集失败: {last_error}[/red]")

        except ImportError as e:
            last_error = f"httpx 模块导入失败: {e}"
            console.print(f"[red]❌ {last_error}[/red]")

        except Exception as e:
            last_error = f"httpx API 异常: {e}"
            console.print(f"[red]❌ {last_error}[/red]")

        # ═══════════════════════════════════════════════════════════════════════
        # 双方案均失败
        # ═══════════════════════════════════════════════════════════════════════
        console.print("[red]❌ 所有采集方案均失败[/red]")
        console.print("[dim]   可能原因: Cookie 过期、网络问题、平台反爬[/dim]")
        console.print("[dim]   建议: 重新登录小红书并更新 Cookie[/dim]")

        return TemplateResult(
            success=False,
            title="",
            content="",
            output_path="",
            push_status="失败",
            error=f"双方案均失败 - {last_error}",
        )
