"""
Hunter AI 内容工厂 - 配置验证器

功能：
- 验证配置文件完整性
- 检查 API Key 格式
- 检查文件路径有效性
- 生成配置状态报告

使用方法：
    from src.utils.config_validator import ConfigValidator

    validator = ConfigValidator()
    result = validator.validate()
    validator.print_report(result)
"""

from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from src.config import CONFIG_YAML, ROOT_DIR, load_yaml_config

console = Console()


@dataclass
class ValidationResult:
    """验证结果"""

    passed: bool = True  # 是否通过验证
    errors: list[str] = field(default_factory=list)  # 错误列表
    warnings: list[str] = field(default_factory=list)  # 警告列表
    info: list[str] = field(default_factory=list)  # 信息列表


class ConfigValidator:
    """
    配置验证器

    功能：
    - 检查必填项
    - 验证 API Key 格式
    - 验证文件路径
    - 检查违禁词数量
    """

    def __init__(self, config_path: Path | None = None):
        """
        初始化验证器

        Args:
            config_path: 配置文件路径（可选）
        """
        self.config_path = config_path or CONFIG_YAML
        self.config = {}

    def validate(self) -> ValidationResult:
        """
        执行完整验证

        Returns:
            ValidationResult: 验证结果
        """
        result = ValidationResult()

        # 检查配置文件是否存在
        if not self.config_path.exists():
            result.passed = False
            result.errors.append(f"配置文件不存在: {self.config_path}")
            return result

        # 加载配置
        try:
            self.config = load_yaml_config()
        except Exception as e:
            result.passed = False
            result.errors.append(f"配置文件解析失败: {e}")
            return result

        # 执行各项检查
        self._check_gemini(result)
        self._check_github(result)
        self._check_twitter(result)
        self._check_pushplus(result)
        self._check_storage(result)
        self._check_content(result)

        return result

    def _check_gemini(self, result: ValidationResult):
        """检查 Gemini 配置"""
        gemini = self.config.get("gemini", {})
        api_key = gemini.get("api_key", "")

        if not api_key:
            result.passed = False
            result.errors.append("gemini.api_key 未配置（必填）")
        elif api_key == "your_gemini_api_key_here":
            result.passed = False
            result.errors.append("gemini.api_key 使用了占位符，请填写真实 API Key")
        else:
            result.info.append(f"Gemini API Key: 已配置 ({api_key[:8]}...)")

        model = gemini.get("model", "")
        if model:
            result.info.append(f"Gemini 模型: {model}")

    def _check_github(self, result: ValidationResult):
        """检查 GitHub 配置"""
        github = self.config.get("github", {})
        token = github.get("token", "")

        if not token:
            result.warnings.append("github.token 未配置（GitHub Hunter 功能需要）")
        elif token.startswith("ghp_your"):
            result.warnings.append("github.token 使用了占位符")
        elif not token.startswith("ghp_") and not token.startswith("github_pat_"):
            result.warnings.append("github.token 格式可能不正确（应以 ghp_ 或 github_pat_ 开头）")
        else:
            result.info.append(f"GitHub Token: 已配置 ({token[:12]}...)")

    def _check_twitter(self, result: ValidationResult):
        """检查 Twitter 配置"""
        twitter = self.config.get("twitter", {})
        cookies_path = twitter.get("cookies_path", "data/cookies.json")

        full_path = ROOT_DIR / cookies_path
        if full_path.exists():
            result.info.append(f"Twitter Cookies: 已配置 ({cookies_path})")
        else:
            result.warnings.append(f"Twitter Cookies 文件不存在: {cookies_path}（痛点雷达功能需要）")

    def _check_pushplus(self, result: ValidationResult):
        """检查 PushPlus 配置"""
        pushplus = self.config.get("pushplus", {})
        token = pushplus.get("token", "")
        enabled = pushplus.get("enabled", True)

        if enabled:
            if not token:
                result.warnings.append("pushplus.token 未配置（微信推送功能需要）")
            elif token == "your_pushplus_token_here":
                result.warnings.append("pushplus.token 使用了占位符")
            else:
                result.info.append(f"PushPlus Token: 已配置 ({token[:8]}...)")
        else:
            result.info.append("PushPlus: 已禁用")

    def _check_storage(self, result: ValidationResult):
        """检查存储配置"""
        storage = self.config.get("storage", {})

        chromadb_path = storage.get("chromadb_path", "data/chromadb")
        output_dir = storage.get("output_dir", "output")

        result.info.append(f"ChromaDB 路径: {chromadb_path}")
        result.info.append(f"输出目录: {output_dir}")

    def _check_content(self, result: ValidationResult):
        """检查内容过滤配置"""
        content = self.config.get("content", {})
        banned_words = content.get("banned_words", [])
        ai_replacements = content.get("ai_word_replacements", {})

        # 向下兼容：检查顶层 banned_words
        if not banned_words:
            banned_words = self.config.get("banned_words", [])

        if len(banned_words) < 10:
            result.warnings.append(f"违禁词数量过少（{len(banned_words)} 个），建议至少 30 个")
        else:
            result.info.append(f"违禁词: {len(banned_words)} 个")

        if len(ai_replacements) < 5:
            result.warnings.append(f"AI痕迹词替换规则过少（{len(ai_replacements)} 条）")
        else:
            result.info.append(f"AI痕迹词替换规则: {len(ai_replacements)} 条")

    def print_report(self, result: ValidationResult):
        """
        打印验证报告

        Args:
            result: 验证结果
        """
        # 标题
        status = "[green]✅ 通过[/green]" if result.passed else "[red]❌ 失败[/red]"
        console.print(Panel.fit(f"配置验证: {status}", style="bold cyan"))

        # 错误
        if result.errors:
            console.print("\n[bold red]❌ 错误 (必须修复)[/bold red]")
            for error in result.errors:
                console.print(f"  • {error}")

        # 警告
        if result.warnings:
            console.print("\n[bold yellow]⚠️ 警告 (建议修复)[/bold yellow]")
            for warning in result.warnings:
                console.print(f"  • {warning}")

        # 信息
        if result.info:
            console.print("\n[bold green]ℹ️ 配置信息[/bold green]")
            for info in result.info:
                console.print(f"  • {info}")

        # 汇总
        console.print(
            f"\n[dim]错误: {len(result.errors)} | 警告: {len(result.warnings)} | 信息: {len(result.info)}[/dim]"
        )


def validate_config() -> ValidationResult:
    """
    便捷函数：验证配置

    Returns:
        ValidationResult: 验证结果
    """
    validator = ConfigValidator()
    return validator.validate()


def print_config_report():
    """便捷函数：打印配置验证报告"""
    validator = ConfigValidator()
    result = validator.validate()
    validator.print_report(result)


# 模块测试
if __name__ == "__main__":
    print_config_report()
