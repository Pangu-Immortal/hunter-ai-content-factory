"""
Hunter AI 内容工厂 - 工作流执行器

功能：
- 执行 6 个 Skill 的 LLM 调用
- 解析 Skill 输出并更新上下文
- 支持断点保存与恢复
- 支持单步执行和全流程执行

使用方法：
    from src.factory.executor import WorkflowExecutor

    executor = WorkflowExecutor()
    result = await executor.run(niche="AI技术", trends=["Agent", "MCP"])

GitHub: https://github.com/Pangu-Immortal/hunter-ai-content-factory
Author: Pangu-Immortal
"""

import asyncio
import json
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.config import settings
from src.factory.workflow import (
    ContentWorkflow,
    PackageOutput,
    PublishOutput,
    ResearchOutput,
    StructureOutput,
    TopicOutput,
    WorkflowContext,
    WriteOutput,
)
from src.intel.utils import get_output_path, get_today_str, push_to_wechat
from src.utils.ai_client import get_ai_client
from src.utils.content_filter import ContentFilter

# 终端输出美化
console = Console()


class SkillExecutor:
    """
    Skill 执行器 - 调用 Gemini 执行各 Skill

    负责：
    - 调用 Gemini API
    - 解析 JSON 响应
    - 处理错误和重试
    """

    def __init__(self):
        """初始化 Skill 执行器"""
        self._init_gemini()
        self.content_filter = ContentFilter(
            banned_words=settings.content.banned_words,
            replacements=settings.content.ai_word_replacements,
        )

    def _init_gemini(self):
        """初始化 AI 客户端（支持官方 Gemini 和 OpenAI 兼容 API）"""
        if not settings.gemini.api_key:
            raise ValueError("API Key 未配置")

        # 使用统一 AI 客户端（自动根据 provider 选择）
        self.client = get_ai_client()
        self.model = settings.gemini.model

    async def execute(self, prompt: str, skill_name: str) -> dict:
        """
        执行 Skill 调用

        Args:
            prompt: 完整的 Prompt
            skill_name: Skill 名称（用于日志）

        Returns:
            dict: 解析后的 JSON 响应
        """
        console.print(f"[cyan]🔄 执行 {skill_name} Skill...[/cyan]")

        try:
            # 调用统一 AI 客户端（同步调用，异步包装）
            response = await asyncio.to_thread(
                self.client.generate_sync,
                prompt,
            )

            # 解析 JSON 响应
            text = response.text.strip()

            # 移除 Markdown 代码块标记
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("\n", 1)[0]
            if text.startswith("json"):
                text = text[4:].strip()

            result = json.loads(text)
            console.print(f"[green]✅ {skill_name} Skill 执行成功[/green]")
            return result

        except json.JSONDecodeError as e:
            console.print(f"[yellow]⚠️ {skill_name} JSON 解析失败: {e}[/yellow]")
            # 返回原始文本作为 fallback
            return {"raw_response": response.text, "parse_error": str(e)}

        except Exception as e:
            console.print(f"[red]❌ {skill_name} 执行失败: {e}[/red]")
            raise


class WorkflowExecutor:
    """
    工作流执行器 - 编排并执行完整工作流

    功能：
    - 依次执行 6 个 Skill
    - 管理上下文数据流转
    - 支持断点保存与恢复
    - 支持回调函数监听进度
    """

    SKILL_ORDER = ["topic", "research", "structure", "write", "package", "publish"]

    def __init__(self):
        """初始化工作流执行器"""
        self.skill_executor = SkillExecutor()
        self.workflow = ContentWorkflow()
        self.checkpoint_dir = settings.storage.checkpoints_path  # 使用配置的路径
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    async def run(
        self,
        niche: str = "",
        trends: list[str] = None,
        resume_from: str | None = None,
        on_skill_complete: Callable | None = None,
    ) -> WorkflowContext:
        """
        执行完整工作流

        Args:
            niche: 细分领域
            trends: 趋势列表
            resume_from: 从指定 Skill 恢复（checkpoint）
            on_skill_complete: Skill 完成回调函数

        Returns:
            WorkflowContext: 完整的工作流上下文
        """
        # 设置输入
        self.workflow.set_input(niche=niche or settings.account.niche, trends=trends or [])

        # 恢复检查点
        start_index = 0
        if resume_from:
            if resume_from in self.SKILL_ORDER:
                start_index = self.SKILL_ORDER.index(resume_from)
                self._load_checkpoint(resume_from)
                console.print(f"[cyan]📌 从 {resume_from} 恢复执行[/cyan]")

        console.print("\n[bold magenta]🚀 开始执行工作流[/bold magenta]")
        console.print(f"   领域: {self.workflow.context.niche}")
        console.print(f"   趋势: {self.workflow.context.trends}")

        # 依次执行各 Skill
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            for i, skill_name in enumerate(self.SKILL_ORDER[start_index:], start=start_index + 1):
                task = progress.add_task(f"[{i}/6] 执行 {skill_name}...", total=None)

                try:
                    await self._execute_skill(skill_name)

                    # 保存检查点
                    self._save_checkpoint(skill_name)

                    # 回调
                    if on_skill_complete:
                        on_skill_complete(skill_name, self.workflow.context)

                    progress.update(task, completed=True)

                except Exception:
                    console.print(f"[red]❌ {skill_name} 执行失败，工作流中断[/red]")
                    console.print(f"[yellow]💡 可使用 --resume {skill_name} 从此处恢复[/yellow]")
                    raise

        console.print("\n[bold green]✅ 工作流执行完成！[/bold green]")
        self.workflow.print_workflow_status()

        return self.workflow.context

    async def run_single(self, skill_name: str) -> dict:
        """
        执行单个 Skill

        Args:
            skill_name: Skill 名称

        Returns:
            dict: Skill 输出
        """
        if skill_name not in self.SKILL_ORDER:
            raise ValueError(f"无效的 Skill 名称: {skill_name}")

        return await self._execute_skill(skill_name)

    async def _execute_skill(self, skill_name: str) -> dict:
        """执行指定 Skill"""
        # 获取 Prompt
        prompt = self._get_prompt(skill_name)

        # 执行
        result = await self.skill_executor.execute(prompt, skill_name)

        # 更新上下文（异步）
        await self._update_context(skill_name, result)

        return result

    def _get_prompt(self, skill_name: str) -> str:
        """获取指定 Skill 的 Prompt"""
        prompt_methods = {
            "topic": self.workflow.get_topic_prompt,
            "research": self.workflow.get_research_prompt,
            "structure": self.workflow.get_structure_prompt,
            "write": self.workflow.get_write_prompt,
            "package": self.workflow.get_package_prompt,
            "publish": lambda: self._get_publish_prompt(),
        }

        method = prompt_methods.get(skill_name)
        if method:
            return method()
        return ""

    def _get_publish_prompt(self) -> str:
        """获取发布 Skill 的 Prompt（特殊处理）"""
        # Publish 不需要 LLM，直接执行推送
        return ""

    async def _update_context(self, skill_name: str, result: dict):
        """更新工作流上下文（异步方法，支持 publish 技能的推送操作）"""
        ctx = self.workflow.context

        if skill_name == "topic":
            ctx.topic = TopicOutput(
                selected_topic=result.get("selected_topic", ""),
                angle=result.get("angle", ""),
                target_audience=result.get("target_audience", ""),
                rationale=result.get("rationale", ""),
                potential_titles=result.get("potential_titles", []),
                keywords=result.get("keywords", []),
            )

        elif skill_name == "research":
            ctx.research = ResearchOutput(
                key_insights=result.get("key_insights", []),
                notes=result.get("notes", ""),
                facts=result.get("facts", []),
                references=result.get("references", []),
                twitter_intel=result.get("twitter_intel", []),
            )

        elif skill_name == "structure":
            ctx.structure = StructureOutput(
                hook=result.get("hook", ""),
                outline=result.get("outline", []),
                closing=result.get("closing", ""),
                total_estimated_length=result.get("total_estimated_length", 0),
            )

        elif skill_name == "write":
            draft = result.get("draft", "")
            # 自动清理 AI 痕迹词
            draft = self.skill_executor.content_filter.auto_clean(draft)
            ctx.write = WriteOutput(
                draft=draft,
                actual_word_count=result.get("actual_word_count", len(draft)),
                readability_score=result.get("readability_score", ""),
            )

        elif skill_name == "package":
            ctx.package = PackageOutput(
                title=result.get("title", ""),
                title_alternatives=result.get("title_alternatives", []),
                summary=result.get("summary", ""),
                cover_image_prompt=result.get("cover_image_prompt", ""),
                draft_with_images=result.get("draft_with_images", ""),
                seo_keywords=result.get("seo_keywords", []),
            )

        elif skill_name == "publish":
            # 执行推送
            await self._execute_publish()

    async def _execute_publish(self):
        """执行发布推送"""
        ctx = self.workflow.context

        # 检查内容
        filter_result = self.skill_executor.content_filter.check(ctx.write.draft)
        if not filter_result.passed:
            console.print(f"[yellow]⚠️ 内容包含 {len(filter_result.found_words)} 个违禁词[/yellow]")
            self.skill_executor.content_filter.print_report(filter_result)

        # 保存文章
        today = get_today_str()
        output_path = get_output_path(f"article_{today}.md", "articles")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# {ctx.package.title}\n\n")
            f.write(ctx.write.draft)
        console.print(f"[green]📄 文章已保存: {output_path}[/green]")

        # 推送到微信
        if settings.push.enabled:
            success = push_to_wechat(
                title=ctx.package.title or ctx.topic.selected_topic,
                content=ctx.write.draft,
            )
            ctx.publish = PublishOutput(
                push_status="成功" if success else "失败",
                push_time=datetime.now().isoformat(),
            )
        else:
            ctx.publish = PublishOutput(
                push_status="已禁用",
                push_time=datetime.now().isoformat(),
            )

    def _save_checkpoint(self, skill_name: str):
        """保存检查点"""
        checkpoint_file = self.checkpoint_dir / f"checkpoint_{skill_name}.json"
        data = {
            "skill": skill_name,
            "timestamp": datetime.now().isoformat(),
            "context": asdict(self.workflow.context),
        }
        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        console.print(f"[dim]💾 检查点已保存: {skill_name}[/dim]")

    def _load_checkpoint(self, skill_name: str) -> bool:
        """加载检查点"""
        # 找到该 skill 之前的最近检查点
        skill_index = self.SKILL_ORDER.index(skill_name)
        if skill_index == 0:
            return False

        prev_skill = self.SKILL_ORDER[skill_index - 1]
        checkpoint_file = self.checkpoint_dir / f"checkpoint_{prev_skill}.json"

        if not checkpoint_file.exists():
            return False

        try:
            with open(checkpoint_file, encoding="utf-8") as f:
                data = json.load(f)

            # 恢复上下文（简化版本，只恢复必要字段）
            ctx_data = data.get("context", {})
            self.workflow.context.niche = ctx_data.get("niche", "")
            self.workflow.context.trends = ctx_data.get("trends", [])

            console.print(f"[green]✅ 已加载检查点: {prev_skill}[/green]")
            return True

        except Exception as e:
            console.print(f"[yellow]⚠️ 加载检查点失败: {e}[/yellow]")
            return False

    def clear_checkpoints(self):
        """清除所有检查点"""
        for f in self.checkpoint_dir.glob("checkpoint_*.json"):
            f.unlink()
        console.print("[green]✅ 检查点已清除[/green]")


async def main():
    """测试工作流执行器"""
    console.print("[bold magenta]🏭 工作流执行器测试[/bold magenta]\n")

    try:
        executor = WorkflowExecutor()

        # 执行完整工作流
        context = await executor.run(
            niche="AI技术",
            trends=["Claude 4", "MCP协议", "Agent编排"],
        )

        # 打印结果
        console.print(f"\n[bold]选题:[/bold] {context.topic.selected_topic}")
        console.print(f"[bold]角度:[/bold] {context.topic.angle}")
        console.print(f"[bold]标题:[/bold] {context.package.title}")
        console.print(f"[bold]字数:[/bold] {context.write.actual_word_count}")
        console.print(f"[bold]推送:[/bold] {context.publish.push_status}")

    except Exception as e:
        console.print(f"[red]❌ 测试失败: {e}[/red]")


if __name__ == "__main__":
    asyncio.run(main())
