"""
Hunter AI 内容工厂 - 模板系统

功能：
- 定义不同内容类型的模板
- 提供统一的模板接口
- 支持全自动执行流程

支持的模板类型：
- github: GitHub 开源推荐（2个项目推荐 + 1个深度解读）
- pain: 痛点解决方案（从 Twitter + Reddit 采集痛点，生成解决方案文章）
- news: 资讯快报（汇总 HackerNews + Twitter + Reddit + GitHub + 小红书 热点）
- xhs: 小红书热门（采集热门笔记，生成种草文章）
- auto: 自动创作（全自动 Intel→分析→生成 流水线）

使用方法：
    from src.templates import get_template, TEMPLATES

    # 获取可用模板列表
    print(TEMPLATES)

    # 获取指定模板
    template = get_template("github")
    await template.run()

GitHub: https://github.com/Pangu-Immortal/hunter-ai-content-factory
Author: Pangu-Immortal
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Type
from rich.console import Console

console = Console()


@dataclass
class TemplateResult:
    """模板执行结果"""
    success: bool              # 是否成功
    title: str                 # 文章标题
    content: str               # 文章内容
    output_path: str           # 输出文件路径
    push_status: str           # 推送状态
    error: Optional[str] = None  # 错误信息


class BaseTemplate(ABC):
    """
    模板基类

    所有内容模板必须继承此类并实现 run() 方法
    """

    # 模板名称
    name: str = "base"

    # 模板描述
    description: str = "基础模板"

    # 是否需要外部数据源
    requires_intel: bool = True

    @abstractmethod
    async def run(self) -> TemplateResult:
        """
        执行模板流程

        Returns:
            TemplateResult: 执行结果
        """
        pass

    def print_header(self):
        """打印模板启动头部"""
        console.print(f"\n[bold magenta]{'=' * 50}[/bold magenta]")
        console.print(f"[bold magenta]🚀 {self.description}[/bold magenta]")
        console.print(f"[bold magenta]{'=' * 50}[/bold magenta]\n")


# ═══════════════════════════════════════════════════════════════════════════════
# 模板注册表
# ═══════════════════════════════════════════════════════════════════════════════

# 模板类注册表（懒加载）
_TEMPLATE_REGISTRY: dict[str, Type[BaseTemplate]] = {}


def register_template(name: str):
    """
    模板注册装饰器

    Args:
        name: 模板名称

    示例:
        @register_template("github")
        class GitHubTemplate(BaseTemplate):
            ...
    """
    def decorator(cls: Type[BaseTemplate]):
        cls.name = name
        _TEMPLATE_REGISTRY[name] = cls
        return cls
    return decorator


def get_template(name: str) -> BaseTemplate:
    """
    获取模板实例

    Args:
        name: 模板名称

    Returns:
        BaseTemplate: 模板实例

    Raises:
        ValueError: 模板不存在
    """
    # 懒加载模板模块
    _load_templates()

    if name not in _TEMPLATE_REGISTRY:
        available = ", ".join(_TEMPLATE_REGISTRY.keys())
        raise ValueError(f"模板 '{name}' 不存在，可用模板: {available}")

    template_class = _TEMPLATE_REGISTRY[name]
    return template_class()


def list_templates() -> dict[str, str]:
    """
    列出所有可用模板

    Returns:
        dict: {模板名称: 模板描述}
    """
    _load_templates()
    return {
        name: cls.description
        for name, cls in _TEMPLATE_REGISTRY.items()
    }


def _load_templates():
    """懒加载所有模板模块"""
    if _TEMPLATE_REGISTRY:
        return  # 已加载

    # 导入模板模块（触发 @register_template 装饰器）
    from src.templates import github_template
    from src.templates import pain_template
    from src.templates import news_template
    from src.templates import xiaohongshu_template
    from src.templates import auto_template


# 模板名称常量
TEMPLATES = {
    "github": "GitHub 开源推荐",
    "pain": "痛点解决方案",
    "news": "资讯快报",
    "xhs": "小红书热门",
    "auto": "自动创作",
}

# 导出
__all__ = [
    "BaseTemplate",
    "TemplateResult",
    "register_template",
    "get_template",
    "list_templates",
    "TEMPLATES",
]
