"""
Hunter AI 内容工厂 - 痛点解决方案模板

功能：
- 从 Twitter 扫描用户痛点和抱怨
- 使用 AI 分析痛点并生成解决方案文章
- 全自动执行：采集 → 分析 → 生成 → 推送

使用方法：
    from src.templates import get_template
    template = get_template("pain")
    result = await template.run()

GitHub: https://github.com/Pangu-Immortal/hunter-ai-content-factory
Author: Pangu-Immortal
"""

from rich.console import Console

from src.config import settings
from src.intel.utils import get_output_path, get_today_str, push_to_wechat
from src.templates import BaseTemplate, TemplateResult, register_template

console = Console()


@register_template("pain")
class PainTemplate(BaseTemplate):
    """
    痛点解决方案模板

    流程：
    1. 从 Twitter 采集用户痛点
    2. AI 分析并提炼核心痛点
    3. 生成解决方案文章
    """

    name = "pain"
    description = "痛点解决方案 - 从用户抱怨中挖掘需求"
    requires_intel = True

    async def run(self) -> TemplateResult:
        """执行痛点解决方案流程"""
        self.print_header()

        try:
            # 导入痛点雷达
            from src.intel.pain_radar import PainRadar

            # 运行痛点雷达
            console.print("[cyan]📡 启动痛点雷达...[/cyan]")
            radar = PainRadar()
            await radar.run()

            # 检查是否有结果
            if radar.pain_points:
                # 生成文章内容
                today = get_today_str()
                title = f"【AI 痛点洞察】{today} 用户最关心的问题"
                content = self._format_pain_article(radar.pain_points)

                # 保存文章
                output_path = get_output_path(f"pain_solution_{today}.md", "articles")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(f"# {title}\n\n{content}")

                # 推送
                push_status = "未推送"
                if settings.push.enabled:
                    success = push_to_wechat(title=title, content=content)
                    push_status = "已推送" if success else "推送失败"

                return TemplateResult(
                    success=True,
                    title=title,
                    content=content,
                    output_path=str(output_path),
                    push_status=push_status,
                )
            else:
                return TemplateResult(
                    success=False,
                    title="",
                    content="",
                    output_path="",
                    push_status="失败",
                    error="未采集到痛点数据",
                )

        except ImportError as e:
            console.print(f"[yellow]⚠️ 痛点雷达模块不可用: {e}[/yellow]")
            return TemplateResult(
                success=False,
                title="",
                content="",
                output_path="",
                push_status="失败",
                error=f"模块导入失败: {e}",
            )

        except Exception as e:
            console.print(f"[red]❌ 痛点模板执行失败: {e}[/red]")
            return TemplateResult(
                success=False,
                title="",
                content="",
                output_path="",
                push_status="失败",
                error=str(e),
            )

    def _format_pain_article(self, results: list) -> str:
        """格式化痛点分析结果为文章"""
        content = []
        content.append("今天从社交媒体上抓取了一些用户的真实反馈，整理出来分享给大家。\n")
        content.append("这些痛点可能正是你在找的产品机会。\n\n")
        content.append("---\n\n")

        for i, result in enumerate(results[:5], 1):  # 最多展示 5 个
            if isinstance(result, dict):
                pain = result.get("pain", result.get("content", ""))
                result.get("source", "Twitter")
                analysis = result.get("analysis", "")
            else:
                pain = str(result)
                analysis = ""

            content.append(f"## 痛点 {i}\n\n")
            content.append(f"> {pain}\n\n")
            if analysis:
                content.append(f"**分析**: {analysis}\n\n")
            content.append("---\n\n")

        content.append("## 小结\n\n")
        content.append("这些痛点背后都藏着机会。下次看到有人抱怨，别只是划过去，想想：这个问题你能不能解决？\n")

        return "".join(content)
