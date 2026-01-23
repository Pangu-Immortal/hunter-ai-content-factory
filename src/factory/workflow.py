"""
Hunter AI 内容工厂 - 内容工厂工作流引擎

功能：
- 编排 6 个 Skill 的执行顺序
- 管理 Skill 之间的数据流转
- 支持单步执行和全流程执行

工作流：Topic → Research → Structure → Write → Package → Publish

GitHub: https://github.com/Pangu-Immortal/hunter-ai-content-factory
Author: Pangu-Immortal
"""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from rich.console import Console

from src.config import settings

# 终端输出美化
console = Console()

# Skill 目录路径
SKILLS_DIR = Path(__file__).parent / "skills"


@dataclass
class TopicOutput:
    """选题 Skill 输出"""
    selected_topic: str = ""  # 选定的主题
    angle: str = ""  # 切入角度
    target_audience: str = ""  # 目标读者
    rationale: str = ""  # 选题理由
    potential_titles: list[str] = field(default_factory=list)  # 备选标题
    keywords: list[str] = field(default_factory=list)  # 关键词


@dataclass
class ResearchOutput:
    """研究 Skill 输出"""
    key_insights: list[str] = field(default_factory=list)  # 核心洞察
    notes: str = ""  # 详细笔记
    facts: list[dict] = field(default_factory=list)  # 关键事实
    references: list[dict] = field(default_factory=list)  # 来源列表
    twitter_intel: list[dict] = field(default_factory=list)  # Twitter 数据


@dataclass
class StructureOutput:
    """结构化 Skill 输出"""
    hook: str = ""  # 开篇钩子
    outline: list[dict] = field(default_factory=list)  # 章节大纲
    closing: str = ""  # 结尾设计
    total_estimated_length: int = 0  # 预估总字数


@dataclass
class WriteOutput:
    """写作 Skill 输出"""
    draft: str = ""  # 完整初稿
    actual_word_count: int = 0  # 实际字数
    readability_score: str = ""  # 可读性评分


@dataclass
class PackageOutput:
    """封装 Skill 输出"""
    title: str = ""  # 最终标题
    title_alternatives: list[str] = field(default_factory=list)  # 备选标题
    summary: str = ""  # 摘要
    cover_image_prompt: str = ""  # 封面图 Prompt
    draft_with_images: str = ""  # 含图片的文章
    seo_keywords: list[str] = field(default_factory=list)  # SEO 关键词


@dataclass
class PublishOutput:
    """发布 Skill 输出"""
    push_status: str = ""  # 推送状态
    push_time: str = ""  # 推送时间
    message_id: str = ""  # 消息 ID
    error_message: str = ""  # 错误信息


@dataclass
class WorkflowContext:
    """工作流上下文 - 存储所有 Skill 的输入输出"""
    # 输入参数
    niche: str = ""  # 细分领域
    trends: list[str] = field(default_factory=list)  # 趋势列表

    # 各阶段输出
    topic: TopicOutput = field(default_factory=TopicOutput)
    research: ResearchOutput = field(default_factory=ResearchOutput)
    structure: StructureOutput = field(default_factory=StructureOutput)
    write: WriteOutput = field(default_factory=WriteOutput)
    package: PackageOutput = field(default_factory=PackageOutput)
    publish: PublishOutput = field(default_factory=PublishOutput)


def load_skill_config() -> dict:
    """
    加载 Skill 全局配置

    Returns:
        dict: 配置字典
    """
    config_path = SKILLS_DIR / "config.json"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def load_skill_prompt(skill_name: str) -> str:
    """
    加载指定 Skill 的 Prompt

    Args:
        skill_name: Skill 名称（如 topic, research）

    Returns:
        str: Prompt 内容
    """
    prompt_path = SKILLS_DIR / skill_name / "prompt.md"
    if prompt_path.exists():
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


class ContentWorkflow:
    """内容工厂工作流引擎"""

    def __init__(self):
        """初始化工作流引擎"""
        self.config = load_skill_config()
        self.context = WorkflowContext()

    def set_input(self, niche: str, trends: list[str]):
        """
        设置工作流输入

        Args:
            niche: 细分领域
            trends: 趋势列表
        """
        self.context.niche = niche or settings.account.niche
        self.context.trends = trends

    def get_topic_prompt(self) -> str:
        """
        获取选题 Skill 的完整 Prompt

        Returns:
            str: 填充后的 Prompt
        """
        template = load_skill_prompt("topic")
        return template.replace("{{niche}}", self.context.niche).replace("{{trends}}", str(self.context.trends))

    def get_research_prompt(self) -> str:
        """
        获取研究 Skill 的完整 Prompt

        Returns:
            str: 填充后的 Prompt
        """
        template = load_skill_prompt("research")
        return template.replace("{{topic}}", self.context.topic.selected_topic).replace("{{keywords}}", str(self.context.topic.keywords))

    def get_structure_prompt(self) -> str:
        """
        获取结构化 Skill 的完整 Prompt

        Returns:
            str: 填充后的 Prompt
        """
        template = load_skill_prompt("structure")
        research_data = {
            "key_insights": self.context.research.key_insights,
            "notes": self.context.research.notes,
            "facts": self.context.research.facts
        }
        return template.replace("{{research_data}}", json.dumps(research_data, ensure_ascii=False)).replace("{{tone}}", self.config.get("account_tone", "")).replace("{{target_audience}}", self.context.topic.target_audience).replace("{{angle}}", self.context.topic.angle)

    def get_write_prompt(self) -> str:
        """
        获取写作 Skill 的完整 Prompt

        Returns:
            str: 填充后的 Prompt
        """
        template = load_skill_prompt("write")
        return template.replace("{{outline}}", json.dumps(self.context.structure.outline, ensure_ascii=False)).replace("{{hook}}", self.context.structure.hook).replace("{{closing}}", self.context.structure.closing).replace("{{research_data}}", self.context.research.notes).replace("{{target_audience}}", self.context.topic.target_audience).replace("{{angle}}", self.context.topic.angle).replace("{{length_constraints}}", json.dumps(self.config.get("article_length", {}), ensure_ascii=False)).replace("{{banned_words}}", str(self.config.get("banned_words", [])))

    def get_package_prompt(self) -> str:
        """
        获取封装 Skill 的完整 Prompt

        Returns:
            str: 填充后的 Prompt
        """
        template = load_skill_prompt("package")
        return template.replace("{{draft}}", self.context.write.draft).replace("{{potential_titles}}", str(self.context.topic.potential_titles)).replace("{{target_audience}}", self.context.topic.target_audience).replace("{{tone}}", self.config.get("account_tone", ""))

    def print_workflow_status(self):
        """打印工作流当前状态"""
        console.print("\n[bold cyan]📋 工作流状态[/bold cyan]")
        console.print(f"  细分领域: {self.context.niche}")
        console.print(f"  选题: {self.context.topic.selected_topic or '未完成'}")
        console.print(f"  研究: {'已完成' if self.context.research.notes else '未完成'}")
        console.print(f"  结构: {'已完成' if self.context.structure.outline else '未完成'}")
        console.print(f"  写作: {'已完成' if self.context.write.draft else '未完成'}")
        console.print(f"  封装: {'已完成' if self.context.package.title else '未完成'}")
        console.print(f"  发布: {self.context.publish.push_status or '未完成'}")


def main():
    """测试工作流引擎"""
    workflow = ContentWorkflow()
    workflow.set_input(niche="AI技术", trends=["Agent", "MCP", "Skill"])
    workflow.print_workflow_status()

    # 打印 Topic Prompt 示例
    console.print("\n[bold cyan]📝 Topic Prompt 示例[/bold cyan]")
    console.print(workflow.get_topic_prompt()[:500] + "...")


if __name__ == "__main__":
    main()
