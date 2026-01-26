"""
摆渡人AI系统 - 常量定义

包含：
- SKILLS_INFO: 6-Skill 工作流数据定义
- load_custom_css(): CSS 样式加载函数
- CUSTOM_CSS: 自定义 CSS 样式

颜色管理说明：
所有颜色统一在 src/static/styles.css 中通过 CSS 变量管理
- 品牌色: --brand-primary, --brand-secondary, --brand-link
- Skill 颜色: --skill-topic, --skill-research, --skill-structure, --skill-write, --skill-package, --skill-publish
- 提示框: --tip-yellow-*, --tip-cyan-*, --tip-blue-*
"""

from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent.parent


def load_custom_css() -> str:
    """从外部文件加载 CSS 样式"""
    css_path = ROOT_DIR / "src" / "static" / "styles.css"
    if css_path.exists():
        return css_path.read_text(encoding="utf-8")
    return ""


# 自定义 CSS 样式
CUSTOM_CSS = load_custom_css()

# 6-Skill 数据定义
# 颜色字段对应 CSS 变量: --skill-{id}
# 例如 topic 对应 var(--skill-topic)
SKILLS_INFO = [
    {
        "id": "topic",
        "emoji": "🎯",
        "name": "Topic 选题",
        "subtitle": "找到值得写的爆款选题",
        "image": "hunter_intro_02.png",
        "description": "从海量信息中找到值得写的爆款选题，分析热点趋势，确定最佳切入角度。",
        "outputs": ["选定主题", "切入角度", "目标读者", "标题候选"],
        "color": "var(--skill-topic, #ff6b6b)",  # CSS 变量引用
        "color_hex": "#ff6b6b",  # 备用十六进制值
    },
    {
        "id": "research",
        "emoji": "🔬",
        "name": "Research 研究",
        "subtitle": "收集高质量素材",
        "image": "hunter_intro_04.png",
        "description": "根据选题搜索相关资料，提取核心观点和数据，验证信息可靠性。",
        "outputs": ["核心洞察", "事实数据", "来源列表", "详细笔记"],
        "color": "var(--skill-research, #4ecdc4)",
        "color_hex": "#4ecdc4",
    },
    {
        "id": "structure",
        "emoji": "🏗️",
        "name": "Structure 结构",
        "subtitle": "设计节奏明快的大纲",
        "image": "hunter_intro_06.png",
        "description": "设计文章骨架和阅读节奏，规划引人入胜的开篇钩子和有力的结尾。",
        "outputs": ["开篇钩子", "章节大纲", "结尾设计", "预估字数"],
        "color": "var(--skill-structure, #45b7d1)",
        "color_hex": "#45b7d1",
    },
    {
        "id": "write",
        "emoji": "✍️",
        "name": "Write 写作",
        "subtitle": "撰写有人味的初稿",
        "image": "hunter_intro_08.png",
        "description": "根据大纲撰写完整文章，融入研究素材，自动过滤 AI 痕迹词。",
        "outputs": ["完整初稿", "实际字数", "可读性评分"],
        "color": "var(--skill-write, #96ceb4)",
        "color_hex": "#96ceb4",
    },
    {
        "id": "package",
        "emoji": "🎁",
        "name": "Package 封装",
        "subtitle": "打造高点击率包装",
        "image": "hunter_intro_10.png",
        "description": "为文章打造吸睛外包装，生成标题选项、精炼摘要、封面图 Prompt。",
        "outputs": ["最终标题", "备选标题", "文章摘要", "封面提示词"],
        "color": "var(--skill-package, #ffeaa7)",
        "color_hex": "#ffeaa7",
    },
    {
        "id": "publish",
        "emoji": "🚀",
        "name": "Publish 发布",
        "subtitle": "一键推送到微信",
        "image": "hunter_intro_12.png",
        "description": "最终违禁词检查，格式化推送内容，通过 PushPlus 一键推送到微信。",
        "outputs": ["推送状态", "推送时间", "消息 ID"],
        "color": "var(--skill-publish, #dfe6e9)",
        "color_hex": "#dfe6e9",
    },
]


def get_image_path(filename: str) -> str:
    """获取图片路径"""
    img_path = ROOT_DIR / "docs" / "images" / filename
    if img_path.exists():
        return str(img_path)
    return ""
