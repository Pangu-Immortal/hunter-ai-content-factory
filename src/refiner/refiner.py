"""
Hunter AI 内容工厂 - 内容精炼模块

功能：
- 深度洗稿（意译重构，非简单替换）
- 去 AI 化表达
- 统一排版
- 封面 Prompt 生成
- 违禁词检查与自动替换

使用方法：
    uv run python -m src.refiner.refiner
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from src.config import settings
from src.utils.ai_client import get_ai_client
from src.utils.content_filter import ContentFilter, FilterResult

# 终端输出美化
console = Console()

# Prompt 模板目录
PROMPTS_DIR = Path(__file__).parent / "prompts"


@dataclass
class RefinerOutput:
    """精炼器输出"""

    title: str = ""  # 优化后的标题
    refined_content: str = ""  # 精炼后的内容
    cover_prompt: str = ""  # 封面图 Prompt
    layout_notes: str = ""  # 排版说明
    keywords: list[str] = field(default_factory=list)  # 提取的关键词
    refining_details: dict = field(default_factory=dict)  # 精炼详情
    filter_result: FilterResult = None  # 违禁词检查结果
    auto_cleaned: bool = False  # 是否经过自动清理


class ContentRefiner:
    """内容精炼器 - 深度洗稿与排版优化"""

    def __init__(self, auto_clean: bool = True):
        """
        初始化内容精炼器

        Args:
            auto_clean: 是否自动清理AI痕迹词，默认开启
        """
        self.auto_clean = auto_clean
        self._init_gemini()
        self._init_filter()

    def _init_gemini(self):
        """初始化 AI 客户端（支持官方 Gemini 和 OpenAI 兼容 API）"""
        if not settings.gemini.api_key:
            console.print("[red]❌ API Key 未配置[/red]")
            raise ValueError("API Key 未配置")

        # 使用统一 AI 客户端
        self.ai_client = get_ai_client()
        provider = "第三方聚合" if settings.gemini.is_openai_compatible else "官方 Gemini"
        console.print(f"[green]✅ AI 客户端连接成功 ({provider})[/green]")

    def _init_filter(self):
        """初始化内容过滤器"""
        self.content_filter = ContentFilter(
            banned_words=settings.content.banned_words,
            replacements=settings.content.ai_word_replacements,
        )
        console.print(f"[green]✅ 内容过滤器已加载 ({len(settings.content.banned_words)} 个违禁词)[/green]")

    def refine(
        self, raw_content: str, target_style: str = "深度、专业且易读", layout_requirements: str = "微信公众号"
    ) -> RefinerOutput:
        """
        精炼内容

        Args:
            raw_content: 原始内容
            target_style: 目标风格
            layout_requirements: 排版要求

        Returns:
            RefinerOutput: 精炼结果
        """
        console.print("[bold cyan]🔄 正在精炼内容...[/bold cyan]")

        prompt = f"""
        # Role: 全能内容精炼与视觉专家 (Content Refiner & Layout Expert)

        ## Profile
        你是一位顶尖的自媒体内容运营专家，擅长"洗稿"（深度改写）、统一排版以及根据内容意境生成极具吸引力的封面提示词。
        你的目标是将原始素材转化为高质量、高传播力且排版精美的成品。

        ## Core Skills

        ### 1. 深度洗稿 (Content Refining)
        - **意译重构**：不只是简单的近义词替换，而是理解核心观点后，用全新的叙述逻辑重组内容。
        - **去AI化**：消除"首先、总之、综上所述"等明显的AI常用词汇，采用更自然、更具情绪价值的表达方式。
        - **风格适配**：采用"{target_style}"的风格。

        ### 2. 统一排版 (Layout Formatting)
        - **结构化**：使用清晰的 H2/H3 标题。
        - **视觉优化**：
          - 关键信息加粗。
          - 适当留白，每段不超过 3 行。
          - 使用引用块 (`>`) 强调金句。
          - 列表化处理复杂信息。
        - **排版规范**：适配 {layout_requirements}。

        ### 3. 封面生成 (Cover Generation)
        - **意境提取**：根据文章核心主题，提取 3-5 个关键词。
        - **提示词编写**：生成高质量的 Midjourney/DALL-E 3 提示词。
        - **风格**：采用"极简主义、高质感 3D 或 商业插画"风格。
        - **比例**：必须包含 "ultra-wide 2.35:1 aspect ratio"。

        ## Task
        请对以下内容进行精炼：

        ```
        {raw_content}
        ```

        ## Output Format
        请返回 JSON 格式，包含：
        - `title`: 优化后的标题
        - `refined_content`: 精炼后的完整内容（Markdown 格式）
        - `cover_prompt`: 封面图英文提示词（包含 2.35:1 比例）
        - `layout_notes`: 排版优化说明
        - `keywords`: 提取的关键词列表
        - `refining_details`: 精炼详情（包括去除的 AI 模式、应用的人性化技巧等）

        请只返回 JSON，不要包含其他文字。
        """

        try:
            response = self.ai_client.generate_sync(prompt)

            # 尝试解析 JSON
            text = response.text.strip()

            # 移除可能的 Markdown 代码块标记
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("\n", 1)[0]
            if text.startswith("json"):
                text = text[4:].strip()

            data = json.loads(text)

            # 获取精炼后的内容
            refined_content = data.get("refined_content", "")
            title = data.get("title", "")

            # 后处理：自动清理AI痕迹词
            auto_cleaned = False
            if self.auto_clean and refined_content:
                refined_content = self.content_filter.auto_clean(refined_content)
                title = self.content_filter.auto_clean(title)
                auto_cleaned = True
                console.print("[green]✅ AI痕迹词已自动清理[/green]")

            # 检查违禁词
            filter_result = self.content_filter.check(refined_content)
            if not filter_result.passed:
                console.print(f"[yellow]⚠️ 发现 {len(filter_result.found_words)} 个违禁词[/yellow]")
                self.content_filter.print_report(filter_result)
            else:
                console.print("[green]✅ 违禁词检查通过[/green]")

            return RefinerOutput(
                title=title,
                refined_content=refined_content,
                cover_prompt=data.get("cover_prompt", ""),
                layout_notes=data.get("layout_notes", ""),
                keywords=data.get("keywords", []),
                refining_details=data.get("refining_details", {}),
                filter_result=filter_result,
                auto_cleaned=auto_cleaned,
            )

        except json.JSONDecodeError as e:
            console.print(f"[yellow]⚠️ JSON 解析失败，返回原始响应: {e}[/yellow]")
            return RefinerOutput(refined_content=response.text, layout_notes="JSON 解析失败，返回原始内容")

        except Exception as e:
            console.print(f"[red]❌ 精炼失败: {e}[/red]")
            raise

    def check_content(self, content: str) -> FilterResult:
        """
        仅检查内容违禁词（不精炼）

        Args:
            content: 待检查的内容

        Returns:
            FilterResult: 检查结果
        """
        return self.content_filter.check(content)

    def clean_content(self, content: str) -> str:
        """
        仅清理AI痕迹词（不精炼）

        Args:
            content: 原始内容

        Returns:
            str: 清理后的内容
        """
        return self.content_filter.auto_clean(content)

    def refine_file(self, file_path: str | Path, output_path: str | Path = None) -> RefinerOutput:
        """
        从文件读取内容并精炼

        Args:
            file_path: 输入文件路径
            output_path: 输出文件路径（可选）

        Returns:
            RefinerOutput: 精炼结果
        """
        path = Path(file_path)

        if not path.exists():
            console.print(f"[red]❌ 文件不存在: {path}[/red]")
            raise FileNotFoundError(f"文件不存在: {path}")

        # 读取文件
        with open(path, encoding="utf-8") as f:
            content = f.read()

        # 精炼
        result = self.refine(content)

        # 保存结果
        if output_path:
            out_path = Path(output_path)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(result.refined_content)
            console.print(f"[green]✅ 精炼结果已保存: {out_path}[/green]")

        return result


def main():
    """测试精炼功能"""
    console.print("[bold magenta]🔄 内容精炼器测试[/bold magenta]\n")

    test_content = """
    震惊！这是一篇必看的文章！

    首先，我们来讨论一下 AI 技术的发展趋势。总的来说，2025 年是 AI 爆发的一年。
    需要注意的是，Agent 技术正在快速发展。综上所述，我们应该关注这个领域。

    权威专家表示，这是100%真实的重大发现！
    """

    try:
        refiner = ContentRefiner()

        # 先测试违禁词检查
        console.print("\n[bold]1. 违禁词检查测试[/bold]")
        result = refiner.check_content(test_content)
        refiner.content_filter.print_report(result)

        # 测试AI痕迹词清理
        console.print("\n[bold]2. AI痕迹词清理测试[/bold]")
        cleaned = refiner.clean_content(test_content)
        console.print(f"[dim]清理后内容:[/dim]\n{cleaned}")

        # 测试完整精炼流程
        console.print("\n[bold]3. 完整精炼测试[/bold]")
        result = refiner.refine(test_content)

        console.print(f"\n[bold]标题:[/bold] {result.title}")
        console.print(f"\n[bold]关键词:[/bold] {result.keywords}")
        console.print(f"\n[bold]封面 Prompt:[/bold] {result.cover_prompt}")
        console.print(f"\n[bold]排版说明:[/bold] {result.layout_notes}")
        console.print(f"\n[bold]自动清理:[/bold] {'是' if result.auto_cleaned else '否'}")
        console.print(f"\n[bold]违禁词检查:[/bold] {'通过' if result.filter_result.passed else '未通过'}")

        if result.refined_content:
            console.print(f"\n[bold]精炼内容预览:[/bold]\n{result.refined_content[:500]}...")

    except Exception as e:
        console.print(f"[red]❌ 测试失败: {e}[/red]")


if __name__ == "__main__":
    main()
