"""
Hunter AI 内容工厂 - 内容过滤器

功能：
- 检查内容中的违禁词
- 自动替换AI痕迹词
- 内容安全检查

使用方法：
    from src.utils.content_filter import ContentFilter

    filter = ContentFilter()
    result = filter.check(content)
    if not result.passed:
        print(f"发现违禁词: {result.found_words}")

    # 自动替换AI痕迹词
    cleaned = filter.auto_clean(content)
"""

import re
from dataclasses import dataclass, field

from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class FilterResult:
    """过滤结果"""

    passed: bool  # 是否通过检查
    found_words: list[str] = field(default_factory=list)  # 发现的违禁词
    locations: list[dict] = field(default_factory=list)  # 违禁词位置信息
    suggestion: str = ""  # 修改建议
    replaced_words: list[str] = field(default_factory=list)  # 已替换的AI痕迹词


class ContentFilter:
    """
    内容过滤器

    功能：
    - 检查违禁词
    - 自动替换AI痕迹词
    - 生成修改建议
    """

    # 默认违禁词列表（与 config.example.yaml 保持同步）
    DEFAULT_BANNED_WORDS = [
        # 标题党/夸张词
        "震惊",
        "必看",
        "100%",
        "绝对",
        "史上最",
        "惊呆了",
        "不转不是中国人",
        "独家曝光",
        "内幕揭秘",
        "重大发现",
        "速看",
        "疯传",
        "刷爆朋友圈",
        "火了",
        "炸了",
        "吓死人",
        # 虚假宣传词
        "权威专家",
        "医学证实",
        "科学证明",
        "国家认证",
        "官方认定",
        "独家秘方",
        "祖传配方",
        "包治百病",
        # 营销诱导词
        "限时优惠",
        "仅剩XX名额",
        "不可错过",
        "立即行动",
        "错过后悔",
        "最后机会",
        "手慢无",
        "赶紧抢",
        # AI生成痕迹词
        "首先",
        "其次",
        "最后",
        "总之",
        "综上所述",
        "值得注意的是",
        "需要指出的是",
        "不难发现",
        "显而易见",
        "毋庸置疑",
        "众所周知",
    ]

    # 默认AI痕迹词替换规则
    DEFAULT_REPLACEMENTS = {
        "首先，": "",
        "其次，": "",
        "最后，": "",
        "总之，": "说到底，",
        "综上所述，": "聊到这里，",
        "综上所述": "说白了",
        "值得注意的是": "有意思的是",
        "需要指出的是": "说句实话",
        "不难发现": "你会发现",
        "显而易见": "明摆着的",
        "毋庸置疑": "没跑了",
        "众所周知": "大家都知道",
    }

    def __init__(
        self,
        banned_words: list[str] | None = None,
        replacements: dict[str, str] | None = None,
    ):
        """
        初始化内容过滤器

        Args:
            banned_words: 违禁词列表（可选，默认使用内置列表）
            replacements: AI痕迹词替换规则（可选，默认使用内置规则）
        """
        self.banned_words = banned_words or self.DEFAULT_BANNED_WORDS
        self.replacements = replacements or self.DEFAULT_REPLACEMENTS

    def check(self, content: str) -> FilterResult:
        """
        检查内容中的违禁词

        Args:
            content: 待检查的内容

        Returns:
            FilterResult: 检查结果
        """
        found_words = []  # 发现的违禁词
        locations = []  # 位置信息

        for word in self.banned_words:
            if word in content:
                found_words.append(word)
                # 查找所有出现位置
                for match in re.finditer(re.escape(word), content):
                    # 提取上下文（前后各20个字符）
                    start = max(0, match.start() - 20)
                    end = min(len(content), match.end() + 20)
                    context = content[start:end]
                    locations.append(
                        {
                            "word": word,
                            "position": match.start(),
                            "context": f"...{context}...",
                        }
                    )

        passed = len(found_words) == 0
        suggestion = ""

        if not passed:
            suggestion = self._generate_suggestion(found_words)

        return FilterResult(
            passed=passed,
            found_words=found_words,
            locations=locations,
            suggestion=suggestion,
        )

    def auto_clean(self, content: str) -> str:
        """
        自动替换AI痕迹词

        Args:
            content: 原始内容

        Returns:
            str: 清理后的内容
        """
        result = content

        for old, new in self.replacements.items():
            result = result.replace(old, new)

        return result

    def check_and_clean(self, content: str) -> tuple[str, FilterResult]:
        """
        检查并清理内容

        先自动替换AI痕迹词，再检查剩余违禁词

        Args:
            content: 原始内容

        Returns:
            tuple: (清理后的内容, 检查结果)
        """
        # 记录替换的词
        replaced_words = []
        cleaned = content

        for old, new in self.replacements.items():
            if old in cleaned:
                replaced_words.append(old)
                cleaned = cleaned.replace(old, new)

        # 检查剩余违禁词（排除已有替换规则的词）
        check_words = [
            word for word in self.banned_words if word not in self.replacements and f"{word}，" not in self.replacements
        ]

        temp_filter = ContentFilter(banned_words=check_words)
        result = temp_filter.check(cleaned)

        # 添加替换记录
        result.replaced_words = replaced_words

        return cleaned, result

    def _generate_suggestion(self, found_words: list[str]) -> str:
        """生成修改建议"""
        suggestions = []

        for word in found_words:
            if word in self.replacements:
                replacement = self.replacements[word]
                if replacement:
                    suggestions.append(f"「{word}」→「{replacement}」")
                else:
                    suggestions.append(f"「{word}」建议删除")
            else:
                suggestions.append(f"「{word}」需要手动替换")

        return "修改建议: " + "; ".join(suggestions)

    def print_report(self, result: FilterResult) -> None:
        """
        打印检查报告（Rich格式）

        Args:
            result: 检查结果
        """
        if result.passed:
            console.print("[bold green]✅ 内容检查通过，未发现违禁词[/bold green]")
            return

        console.print(f"[bold red]❌ 发现 {len(result.found_words)} 个违禁词[/bold red]\n")

        # 创建表格
        table = Table(title="违禁词详情")
        table.add_column("违禁词", style="red")
        table.add_column("位置", style="cyan")
        table.add_column("上下文", style="dim")

        for loc in result.locations:
            table.add_row(loc["word"], str(loc["position"]), loc["context"])

        console.print(table)
        console.print(f"\n[yellow]{result.suggestion}[/yellow]")


def check_content(content: str, banned_words: list[str] | None = None) -> FilterResult:
    """
    便捷函数：检查内容违禁词

    Args:
        content: 待检查内容
        banned_words: 违禁词列表（可选）

    Returns:
        FilterResult: 检查结果
    """
    filter_instance = ContentFilter(banned_words=banned_words)
    return filter_instance.check(content)


def clean_ai_markers(content: str, replacements: dict[str, str] | None = None) -> str:
    """
    便捷函数：清理AI痕迹词

    Args:
        content: 原始内容
        replacements: 替换规则（可选）

    Returns:
        str: 清理后的内容
    """
    filter_instance = ContentFilter(replacements=replacements)
    return filter_instance.auto_clean(content)


# 模块测试
if __name__ == "__main__":
    test_content = """
    震惊！这篇文章必看！

    首先，让我们来看看这个重大发现。
    其次，权威专家表示这是100%真实的。
    最后，综上所述，这个独家曝光的内容值得注意的是非常重要。

    不转不是中国人！限时优惠，错过后悔！
    """

    print("=" * 60)
    print("原始内容:")
    print(test_content)
    print("=" * 60)

    filter_instance = ContentFilter()

    # 检查违禁词
    result = filter_instance.check(test_content)
    filter_instance.print_report(result)

    print("\n" + "=" * 60)
    print("自动清理后:")
    cleaned = filter_instance.auto_clean(test_content)
    print(cleaned)
    print("=" * 60)

    # 再次检查
    result2 = filter_instance.check(cleaned)
    filter_instance.print_report(result2)
