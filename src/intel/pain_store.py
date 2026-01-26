"""
Hunter AI 内容工厂 - 痛点数据存储模块

功能：
- SQLite 结构化存储所有采集的痛点
- 标签系统（产品、类型、严重程度等）
- 相似痛点检测与合并
- ChromaDB 向量相似度辅助

表结构：
- pain_points: 痛点主表
- 标签使用 JSON 数组存储（简化设计）

使用方法：
    from src.intel.pain_store import PainStore

    store = PainStore()
    store.add_pain(content="...", source="twitter", ...)
    similar = store.find_similar("...")

GitHub: https://github.com/Pangu-Immortal/hunter-ai-content-factory
Author: Pangu-Immortal
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table
from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config import ROOT_DIR
from src.intel.utils import get_chromadb_client

# 终端输出
console = Console()

# SQLAlchemy 基类
Base = declarative_base()

# 数据库路径
DB_PATH = ROOT_DIR / "data" / "pain_points.db"


# ═══════════════════════════════════════════════════════════════════════════════
# 数据模型定义
# ═══════════════════════════════════════════════════════════════════════════════


class PainPointModel(Base):
    """
    痛点数据表

    存储所有采集的用户痛点，支持标签、分类、合并等功能
    """

    __tablename__ = "pain_points"

    # 主键：基于内容的唯一 ID
    id = Column(String(64), primary_key=True, comment="唯一ID（内容hash）")

    # 核心内容
    content = Column(Text, nullable=False, comment="痛点原文内容")
    content_normalized = Column(Text, comment="标准化后的内容（去除噪音）")

    # 来源信息
    source = Column(String(32), nullable=False, comment="来源平台: twitter/weibo/xiaohongshu/hackernews")
    platform = Column(String(32), comment="相关产品: ChatGPT/Claude/DeepSeek/Gemini等")
    author = Column(String(128), comment="原作者")
    original_url = Column(String(512), comment="原始链接")

    # 标签系统（JSON 数组）
    tags = Column(JSON, default=list, comment="标签列表")

    # 分类与严重程度
    category = Column(String(32), comment="问题分类: 性能/准确性/功能/体验/定价/其他")
    severity = Column(String(16), default="minor", comment="严重程度: blocker/major/minor/enhancement")

    # AI 分析结果
    ai_analysis = Column(Text, comment="AI 分析摘要")
    ai_solution = Column(Text, comment="AI 建议的解决方案")

    # 统计信息
    frequency = Column(Integer, default=1, comment="出现频率（相似痛点合并时累加）")
    similarity_score = Column(Float, comment="与主痛点的相似度（合并时记录）")

    # 合并追踪
    merged_from = Column(JSON, default=list, comment="合并来源ID列表")
    is_primary = Column(Integer, default=1, comment="是否为主痛点（1=主，0=已合并到其他）")
    merged_to = Column(String(64), comment="合并到哪个主痛点（如果is_primary=0）")

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment="首次发现时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="最后更新时间")

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "content": self.content,
            "source": self.source,
            "platform": self.platform,
            "author": self.author,
            "tags": self.tags or [],
            "category": self.category,
            "severity": self.severity,
            "frequency": self.frequency,
            "ai_analysis": self.ai_analysis,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 标签定义
# ═══════════════════════════════════════════════════════════════════════════════

# 产品标签
PRODUCT_TAGS = [
    "ChatGPT",
    "Claude",
    "Gemini",
    "DeepSeek",
    "Cursor",
    "Windsurf",
    "Copilot",
    "Perplexity",
    "Midjourney",
    "DALL-E",
    "Stable Diffusion",
    "LangChain",
    "LlamaIndex",
    "OpenAI API",
    "Anthropic API",
]

# 问题类型标签
CATEGORY_TAGS = {
    "性能": ["slow", "timeout", "lag", "latency", "速度慢", "卡顿", "超时"],
    "准确性": ["wrong", "incorrect", "hallucination", "错误", "不准确", "胡说"],
    "功能": ["missing", "not working", "broken", "功能缺失", "不工作", "坏了"],
    "体验": ["confusing", "hard to use", "ugly", "难用", "界面", "体验差"],
    "定价": ["expensive", "pricing", "cost", "贵", "收费", "价格"],
    "API": ["api error", "rate limit", "quota", "接口", "限流", "配额"],
    "稳定性": ["crash", "down", "outage", "崩溃", "宕机", "不稳定"],
}

# 严重程度
SEVERITY_KEYWORDS = {
    "blocker": ["can't", "impossible", "completely", "totally", "完全不能", "彻底"],
    "major": ["very", "really", "seriously", "非常", "严重", "很"],
    "minor": ["sometimes", "occasionally", "slightly", "有时", "偶尔", "轻微"],
}


# ═══════════════════════════════════════════════════════════════════════════════
# 痛点存储类
# ═══════════════════════════════════════════════════════════════════════════════


class PainStore:
    """
    痛点数据存储

    功能：
    - SQLite 结构化存储
    - ChromaDB 向量相似度检索
    - 自动标签推断
    - 相似痛点合并
    """

    # 相似度阈值：高于此值认为是相似痛点
    SIMILARITY_THRESHOLD = 0.80

    def __init__(self, db_path: Path = None):
        """
        初始化痛点存储

        Args:
            db_path: 数据库路径，默认使用 data/pain_points.db
        """
        self.db_path = db_path or DB_PATH
        self._init_database()
        self._init_chromadb()

    def _init_database(self):
        """初始化 SQLite 数据库"""
        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建引擎和会话
        self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        session_factory = sessionmaker(bind=self.engine)
        self.session = session_factory()

        # 统计现有数据
        count = self.session.query(PainPointModel).filter(PainPointModel.is_primary == 1).count()
        console.print(f"[green]✅ 痛点数据库连接成功 (已存储 {count} 个主痛点)[/green]")

    def _init_chromadb(self):
        """初始化 ChromaDB 向量数据库（用于相似度检索）"""
        try:
            client = get_chromadb_client()
            self.vector_collection = client.get_or_create_collection(
                name="pain_points_vectors", metadata={"description": "痛点向量存储，用于语义相似度检索"}
            )
            console.print("[green]✅ ChromaDB 向量索引连接成功[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠️ ChromaDB 初始化失败，将禁用相似度检索: {e}[/yellow]")
            self.vector_collection = None

    def _generate_id(self, content: str, source: str) -> str:
        """生成唯一ID"""
        raw = f"{source}:{content}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def _infer_tags(self, content: str) -> list[str]:
        """
        从内容推断标签

        Args:
            content: 痛点内容

        Returns:
            list[str]: 推断的标签列表
        """
        tags = []
        content_lower = content.lower()

        # 检测产品标签
        for product in PRODUCT_TAGS:
            if product.lower() in content_lower:
                tags.append(f"product:{product}")

        # 检测问题类型
        for category, keywords in CATEGORY_TAGS.items():
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    tags.append(f"category:{category}")
                    break

        return list(set(tags))  # 去重

    def _infer_category(self, content: str) -> str:
        """推断问题分类"""
        content_lower = content.lower()
        for category, keywords in CATEGORY_TAGS.items():
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    return category
        return "其他"

    def _infer_severity(self, content: str) -> str:
        """推断严重程度"""
        content_lower = content.lower()
        for severity, keywords in SEVERITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    return severity
        return "minor"

    def _infer_platform(self, content: str) -> str:
        """推断相关产品"""
        content_lower = content.lower()
        for product in PRODUCT_TAGS:
            if product.lower() in content_lower:
                return product
        return None

    def find_similar(self, content: str, threshold: float = None) -> PainPointModel | None:
        """
        查找相似痛点

        使用 ChromaDB 向量相似度搜索，找到最相似的现有痛点

        Args:
            content: 痛点内容
            threshold: 相似度阈值（默认使用类属性）

        Returns:
            PainPointModel: 最相似的痛点，如果没有则返回 None
        """
        if self.vector_collection is None:
            return None

        threshold = threshold or self.SIMILARITY_THRESHOLD

        try:
            # 向量相似度搜索
            results = self.vector_collection.query(
                query_texts=[content], n_results=1, include=["distances", "metadatas"]
            )

            if results and results["distances"] and results["distances"][0]:
                # ChromaDB 返回 L2 距离，转换为相似度
                distance = results["distances"][0][0]
                similarity = 1 / (1 + distance)

                if similarity >= threshold:
                    pain_id = results["ids"][0][0]
                    pain = (
                        self.session.query(PainPointModel)
                        .filter(PainPointModel.id == pain_id, PainPointModel.is_primary == 1)
                        .first()
                    )

                    if pain:
                        console.print(f"[yellow]🔍 发现相似痛点 (相似度: {similarity:.1%})[/yellow]")
                        return pain

            return None

        except Exception as e:
            console.print(f"[dim]⚠️ 相似度检索失败: {e}[/dim]")
            return None

    def add_pain(
        self,
        content: str,
        source: str,
        author: str = None,
        platform: str = None,
        original_url: str = None,
        tags: list[str] = None,
        category: str = None,
        severity: str = None,
        ai_analysis: str = None,
        auto_merge: bool = True,
    ) -> tuple[PainPointModel, bool]:
        """
        添加痛点

        如果发现相似痛点，会自动合并（更新频率、合并标签）

        Args:
            content: 痛点内容
            source: 来源平台
            author: 作者
            platform: 相关产品
            original_url: 原始链接
            tags: 标签列表
            category: 问题分类
            severity: 严重程度
            ai_analysis: AI 分析结果
            auto_merge: 是否自动合并相似痛点

        Returns:
            tuple[PainPointModel, bool]: (痛点对象, 是否为新增)
        """
        # 自动推断缺失字段
        inferred_tags = self._infer_tags(content)
        final_tags = list(set((tags or []) + inferred_tags))

        platform = platform or self._infer_platform(content)
        category = category or self._infer_category(content)
        severity = severity or self._infer_severity(content)

        # 检查相似痛点
        if auto_merge:
            similar = self.find_similar(content)
            if similar:
                # 合并到现有痛点
                return self._merge_pain(similar, content, source, author, final_tags, ai_analysis)

        # 创建新痛点
        pain_id = self._generate_id(content, source)

        # 检查是否已存在（精确匹配）
        existing = self.session.query(PainPointModel).filter(PainPointModel.id == pain_id).first()
        if existing:
            # 更新频率
            existing.frequency += 1
            existing.updated_at = datetime.now()
            # 合并标签
            existing_tags = existing.tags or []
            existing.tags = list(set(existing_tags + final_tags))
            self.session.commit()
            console.print(f"[cyan]📝 更新已有痛点 (频率: {existing.frequency})[/cyan]")
            return existing, False

        # 新建痛点
        pain = PainPointModel(
            id=pain_id,
            content=content,
            content_normalized=content.lower().strip(),
            source=source,
            platform=platform,
            author=author,
            original_url=original_url,
            tags=final_tags,
            category=category,
            severity=severity,
            ai_analysis=ai_analysis,
            frequency=1,
            is_primary=1,
            merged_from=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        self.session.add(pain)
        self.session.commit()

        # 同步到向量数据库
        self._add_to_vector_db(pain)

        console.print(f"[green]💾 新增痛点: {content[:40]}... [标签: {', '.join(final_tags[:3])}][/green]")
        return pain, True

    def _merge_pain(
        self,
        primary: PainPointModel,
        new_content: str,
        new_source: str,
        new_author: str,
        new_tags: list[str],
        new_analysis: str = None,
    ) -> tuple[PainPointModel, bool]:
        """
        合并痛点到主痛点

        Args:
            primary: 主痛点
            new_content: 新内容
            new_source: 新来源
            new_author: 新作者
            new_tags: 新标签
            new_analysis: 新分析

        Returns:
            tuple[PainPointModel, bool]: (主痛点, False表示合并而非新增)
        """
        # 更新主痛点
        primary.frequency += 1
        primary.updated_at = datetime.now()

        # 合并标签
        existing_tags = primary.tags or []
        primary.tags = list(set(existing_tags + new_tags))

        # 记录合并来源
        new_id = self._generate_id(new_content, new_source)
        merged_from = primary.merged_from or []
        if new_id not in merged_from:
            merged_from.append(new_id)
            primary.merged_from = merged_from

        # 更新 AI 分析（如果新的更详细）
        if new_analysis and (not primary.ai_analysis or len(new_analysis) > len(primary.ai_analysis)):
            primary.ai_analysis = new_analysis

        self.session.commit()

        console.print(f"[cyan]🔗 合并到主痛点 (频率: {primary.frequency}, 标签: {len(primary.tags)})[/cyan]")
        return primary, False

    def _add_to_vector_db(self, pain: PainPointModel):
        """添加到向量数据库"""
        if self.vector_collection is None:
            return

        try:
            self.vector_collection.upsert(
                ids=[pain.id],
                documents=[pain.content],
                metadatas=[
                    {
                        "source": pain.source,
                        "platform": pain.platform or "",
                        "category": pain.category or "",
                        "severity": pain.severity or "",
                    }
                ],
            )
        except Exception as e:
            console.print(f"[dim]⚠️ 向量存储失败: {e}[/dim]")

    def update_ai_analysis(self, pain_id: str, analysis: str, solution: str = None):
        """
        更新 AI 分析结果

        Args:
            pain_id: 痛点 ID
            analysis: AI 分析摘要
            solution: AI 建议的解决方案
        """
        pain = self.session.query(PainPointModel).filter(PainPointModel.id == pain_id).first()
        if pain:
            pain.ai_analysis = analysis
            if solution:
                pain.ai_solution = solution
            pain.updated_at = datetime.now()
            self.session.commit()

    def get_by_platform(self, platform: str, limit: int = 50) -> list[PainPointModel]:
        """按产品获取痛点"""
        return (
            self.session.query(PainPointModel)
            .filter(PainPointModel.platform == platform, PainPointModel.is_primary == 1)
            .order_by(PainPointModel.frequency.desc())
            .limit(limit)
            .all()
        )

    def get_by_category(self, category: str, limit: int = 50) -> list[PainPointModel]:
        """按分类获取痛点"""
        return (
            self.session.query(PainPointModel)
            .filter(PainPointModel.category == category, PainPointModel.is_primary == 1)
            .order_by(PainPointModel.frequency.desc())
            .limit(limit)
            .all()
        )

    def get_top_pains(self, limit: int = 20) -> list[PainPointModel]:
        """获取高频痛点"""
        return (
            self.session.query(PainPointModel)
            .filter(PainPointModel.is_primary == 1)
            .order_by(PainPointModel.frequency.desc())
            .limit(limit)
            .all()
        )

    def get_recent_pains(self, days: int = 7, limit: int = 50) -> list[PainPointModel]:
        """获取最近的痛点"""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        return (
            self.session.query(PainPointModel)
            .filter(PainPointModel.created_at >= cutoff, PainPointModel.is_primary == 1)
            .order_by(PainPointModel.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_stats(self) -> dict:
        """获取统计信息"""
        total = self.session.query(PainPointModel).filter(PainPointModel.is_primary == 1).count()

        # 按产品统计
        from sqlalchemy import func

        platform_stats = (
            self.session.query(
                PainPointModel.platform, func.count(PainPointModel.id), func.sum(PainPointModel.frequency)
            )
            .filter(PainPointModel.is_primary == 1, PainPointModel.platform.isnot(None))
            .group_by(PainPointModel.platform)
            .all()
        )

        # 按分类统计
        category_stats = (
            self.session.query(
                PainPointModel.category, func.count(PainPointModel.id), func.sum(PainPointModel.frequency)
            )
            .filter(PainPointModel.is_primary == 1, PainPointModel.category.isnot(None))
            .group_by(PainPointModel.category)
            .all()
        )

        # 按严重程度统计
        severity_stats = (
            self.session.query(PainPointModel.severity, func.count(PainPointModel.id))
            .filter(PainPointModel.is_primary == 1)
            .group_by(PainPointModel.severity)
            .all()
        )

        return {
            "total_pains": total,
            "by_platform": {p: {"count": c, "frequency": f} for p, c, f in platform_stats if p},
            "by_category": {c: {"count": cnt, "frequency": f} for c, cnt, f in category_stats if c},
            "by_severity": {s: cnt for s, cnt in severity_stats if s},
        }

    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()

        console.print("\n[bold magenta]📊 痛点数据库统计[/bold magenta]\n")
        console.print(f"总痛点数: [bold]{stats['total_pains']}[/bold]\n")

        # 按产品统计
        if stats["by_platform"]:
            table = Table(title="按产品统计")
            table.add_column("产品", style="cyan")
            table.add_column("痛点数", justify="right")
            table.add_column("总频率", justify="right")

            for platform, data in sorted(stats["by_platform"].items(), key=lambda x: x[1]["frequency"], reverse=True):
                table.add_row(platform, str(data["count"]), str(data["frequency"]))

            console.print(table)

        # 按分类统计
        if stats["by_category"]:
            table = Table(title="按问题类型统计")
            table.add_column("类型", style="yellow")
            table.add_column("痛点数", justify="right")
            table.add_column("总频率", justify="right")

            for category, data in sorted(stats["by_category"].items(), key=lambda x: x[1]["frequency"], reverse=True):
                table.add_row(category, str(data["count"]), str(data["frequency"]))

            console.print(table)

    def export_to_json(self, output_path: Path = None) -> Path:
        """导出为 JSON"""
        output_path = output_path or (ROOT_DIR / "output" / "pain_points_export.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        pains = self.session.query(PainPointModel).filter(PainPointModel.is_primary == 1).all()
        data = {
            "exported_at": datetime.now().isoformat(),
            "total": len(pains),
            "pain_points": [p.to_dict() for p in pains],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        console.print(f"[green]📦 已导出 {len(pains)} 个痛点到: {output_path}[/green]")
        return output_path

    def close(self):
        """关闭数据库连接"""
        self.session.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 测试入口
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    """测试痛点存储"""
    console.print("[bold magenta]🧪 痛点存储模块测试[/bold magenta]\n")

    store = PainStore()

    # 测试添加痛点
    test_pains = [
        {
            "content": "ChatGPT is so slow today, I can't even complete a simple query",
            "source": "twitter",
            "author": "user123",
        },
        {
            "content": "Claude keeps giving me wrong answers about Python code",
            "source": "twitter",
            "author": "dev456",
        },
        {
            "content": "ChatGPT response time is terrible, taking forever to load",  # 应该与第一个合并
            "source": "twitter",
            "author": "user789",
        },
        {
            "content": "DeepSeek API is down again, third time this week",
            "source": "hackernews",
            "author": "techie",
        },
    ]

    console.print("[bold]1. 添加测试痛点[/bold]\n")
    for pain_data in test_pains:
        store.add_pain(**pain_data)
        console.print("")

    console.print("\n[bold]2. 查看统计[/bold]")
    store.print_stats()

    console.print("\n[bold]3. 获取高频痛点[/bold]")
    top_pains = store.get_top_pains(5)
    for p in top_pains:
        console.print(f"  [{p.frequency}次] {p.content[:50]}...")

    store.close()


if __name__ == "__main__":
    main()
