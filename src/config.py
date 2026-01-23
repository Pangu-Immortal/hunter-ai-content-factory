"""
Hunter AI 内容工厂 - 统一配置管理模块

功能：
- 从 config.yaml 文件加载配置（推荐）
- 向下兼容 .env 文件
- 提供类型安全的配置访问
- 支持默认值和配置验证

配置文件优先级：
1. config.yaml（推荐，可读性好）
2. .env（向下兼容旧配置）
3. 默认值

GitHub: https://github.com/Pangu-Immortal/hunter-ai-content-factory
Author: Pangu-Immortal
"""

import yaml
from pathlib import Path
from functools import lru_cache
from dataclasses import dataclass, field
from typing import Optional


# 项目根目录
ROOT_DIR = Path(__file__).parent.parent

# 配置文件路径
CONFIG_YAML = ROOT_DIR / "config.yaml"
CONFIG_EXAMPLE = ROOT_DIR / "config.example.yaml"
ENV_FILE = ROOT_DIR / ".env"


def load_yaml_config() -> dict:
    """
    加载 YAML 配置文件

    Returns:
        dict: 配置字典，如果文件不存在则返回空字典
    """
    if CONFIG_YAML.exists():
        with open(CONFIG_YAML, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


def load_env_config() -> dict:
    """
    从 .env 文件加载配置（向下兼容）

    Returns:
        dict: 转换为嵌套结构的配置字典
    """
    if not ENV_FILE.exists():
        return {}

    env_vars = {}
    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()

    # 转换为嵌套结构（与 YAML 格式一致）
    return {
        'gemini': {
            'api_key': env_vars.get('GEMINI_API_KEY', ''),
            'model': env_vars.get('GEMINI_MODEL', 'gemini-2.0-flash'),
        },
        'github': {
            'token': env_vars.get('GITHUB_TOKEN', ''),
            'min_stars': int(env_vars.get('GITHUB_MIN_STARS', 200)),
            'days_since_update': int(env_vars.get('GITHUB_DAYS_SINCE_UPDATE', 180)),
        },
        'twitter': {
            'cookies_path': env_vars.get('TWITTER_COOKIES_PATH', 'data/cookies.json'),
        },
        'pushplus': {
            'token': env_vars.get('PUSHPLUS_TOKEN', ''),
            'enabled': True,
        },
        'storage': {
            'chromadb_path': env_vars.get('CHROMADB_PATH', 'data/chromadb'),
            'output_dir': env_vars.get('OUTPUT_DIR', 'output'),
        },
        'account': {
            'name': env_vars.get('ACCOUNT_NAME', 'AI技术前沿'),
            'tone': env_vars.get('ACCOUNT_TONE', '专业且引人入胜'),
            'niche': env_vars.get('DEFAULT_NICHE', 'AI技术'),
            'min_length': int(env_vars.get('ARTICLE_MIN_LENGTH', 1500)),
            'max_length': int(env_vars.get('ARTICLE_MAX_LENGTH', 2500)),
            'max_title_length': int(env_vars.get('MAX_TITLE_LENGTH', 22)),
        },
        'system': {
            'log_level': env_vars.get('LOG_LEVEL', 'INFO'),
        },
        'content': {
            'banned_words': [],  # .env 不支持列表，使用默认值
            'ai_word_replacements': {},  # .env 不支持字典，使用默认值
        },
    }


@dataclass
class GeminiConfig:
    """AI 大模型配置"""
    provider: str = "official"           # API 提供商: official / openai_compatible
    base_url: str = ""                   # API 基础地址（openai_compatible 模式）
    api_key: str = ""                    # API 密钥
    model: str = "gemini-2.0-flash"      # 模型名称
    image_model: str = ""                # 图片生成模型（留空则使用备选方案）

    @property
    def is_openai_compatible(self) -> bool:
        """是否使用 OpenAI 兼容 API"""
        return self.provider == "openai_compatible" and bool(self.base_url)

    @property
    def has_image_model(self) -> bool:
        """是否配置了图片生成模型"""
        return bool(self.image_model)


@dataclass
class GitHubConfig:
    """GitHub API 配置"""
    token: str = ""  # GitHub Token
    min_stars: int = 200  # 最小 Star 数
    days_since_update: int = 180  # 更新天数阈值


@dataclass
class TwitterConfig:
    """Twitter 配置"""
    cookies_path: str = "data/cookies.json"  # Cookies 文件路径

    @property
    def cookies_file(self) -> Path:
        """获取 Cookies 文件完整路径"""
        return ROOT_DIR / self.cookies_path


@dataclass
class XiaohongshuConfig:
    """小红书配置"""
    cookies: str = ""                      # Cookie 字符串
    default_keyword: str = "AI工具"        # 默认搜索关键词
    default_style: str = "种草"            # 默认文章风格


@dataclass
class PushConfig:
    """PushPlus 推送配置"""
    token: str = ""  # PushPlus Token
    enabled: bool = True  # 是否启用推送


@dataclass
class StorageConfig:
    """数据存储配置"""
    chromadb_path: str = "data/chromadb"  # ChromaDB 路径
    output_dir: str = "output"  # 输出目录

    @property
    def chromadb_dir(self) -> Path:
        """获取 ChromaDB 完整路径"""
        return ROOT_DIR / self.chromadb_path

    @property
    def output_path(self) -> Path:
        """获取输出目录完整路径"""
        return ROOT_DIR / self.output_dir


@dataclass
class AccountConfig:
    """公众号账号配置"""
    name: str = "AI技术前沿"  # 账号名称
    tone: str = "专业且引人入胜"  # 语气风格
    niche: str = "AI技术"  # 细分领域
    min_length: int = 1500  # 文章最小长度
    max_length: int = 2500  # 文章最大长度
    max_title_length: int = 22  # 标题最大长度


@dataclass
class SystemConfig:
    """系统配置"""
    log_level: str = "INFO"  # 日志级别


@dataclass
class ContentConfig:
    """内容过滤配置"""
    banned_words: list = field(default_factory=list)          # 违禁词列表
    ai_word_replacements: dict = field(default_factory=dict)  # AI痕迹词替换规则

    def __post_init__(self):
        """初始化默认值（从 ContentFilter 同步）"""
        if not self.banned_words:
            # 默认违禁词列表（与 config.example.yaml 保持同步）
            self.banned_words = [
                # 标题党/夸张词
                "震惊", "必看", "100%", "绝对", "史上最", "惊呆了",
                "不转不是中国人", "独家曝光", "内幕揭秘", "重大发现",
                "速看", "疯传", "刷爆朋友圈", "火了", "炸了", "吓死人",
                # 虚假宣传词
                "权威专家", "医学证实", "科学证明", "国家认证", "官方认定",
                "独家秘方", "祖传配方", "包治百病",
                # 营销诱导词
                "限时优惠", "仅剩XX名额", "不可错过", "立即行动",
                "错过后悔", "最后机会", "手慢无", "赶紧抢",
                # AI生成痕迹词
                "首先", "其次", "最后", "总之", "综上所述",
                "值得注意的是", "需要指出的是", "不难发现", "显而易见",
                "毋庸置疑", "众所周知",
            ]
        if not self.ai_word_replacements:
            self.ai_word_replacements = {
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


@dataclass
class Settings:
    """主配置类 - 聚合所有子配置"""
    gemini: GeminiConfig = field(default_factory=GeminiConfig)              # Gemini 配置
    github: GitHubConfig = field(default_factory=GitHubConfig)              # GitHub 配置
    twitter: TwitterConfig = field(default_factory=TwitterConfig)           # Twitter 配置
    xiaohongshu: XiaohongshuConfig = field(default_factory=XiaohongshuConfig)  # 小红书配置
    push: PushConfig = field(default_factory=PushConfig)                    # 推送配置
    storage: StorageConfig = field(default_factory=StorageConfig)           # 存储配置
    account: AccountConfig = field(default_factory=AccountConfig)           # 账号配置
    system: SystemConfig = field(default_factory=SystemConfig)              # 系统配置
    content: ContentConfig = field(default_factory=ContentConfig)           # 内容过滤配置

    # 配置来源标识
    config_source: str = "default"  # yaml, env, default

    # 向下兼容：直接访问 banned_words
    @property
    def banned_words(self) -> list:
        """便捷访问违禁词列表"""
        return self.content.banned_words

    @classmethod
    def from_dict(cls, data: dict, source: str = "default") -> "Settings":
        """
        从字典创建配置实例

        Args:
            data: 配置字典
            source: 配置来源标识

        Returns:
            Settings: 配置实例
        """
        gemini_data = data.get('gemini', {})
        github_data = data.get('github', {})
        twitter_data = data.get('twitter', {})
        xiaohongshu_data = data.get('xiaohongshu', {})
        push_data = data.get('pushplus', {})
        storage_data = data.get('storage', {})
        account_data = data.get('account', {})
        system_data = data.get('system', {})
        content_data = data.get('content', {})

        # 向下兼容：如果顶层有 banned_words，使用它
        banned_words = content_data.get('banned_words', []) or data.get('banned_words', [])
        ai_replacements = content_data.get('ai_word_replacements', {})

        return cls(
            gemini=GeminiConfig(
                provider=gemini_data.get('provider', 'official'),
                base_url=gemini_data.get('base_url', ''),
                api_key=gemini_data.get('api_key', ''),
                model=gemini_data.get('model', 'gemini-2.0-flash'),
                image_model=gemini_data.get('image_model', ''),
            ),
            github=GitHubConfig(
                token=github_data.get('token', ''),
                min_stars=github_data.get('min_stars', 200),
                days_since_update=github_data.get('days_since_update', 180),
            ),
            twitter=TwitterConfig(
                cookies_path=twitter_data.get('cookies_path', 'data/cookies.json'),
            ),
            xiaohongshu=XiaohongshuConfig(
                cookies=xiaohongshu_data.get('cookies', ''),
                default_keyword=xiaohongshu_data.get('default_keyword', 'AI工具'),
                default_style=xiaohongshu_data.get('default_style', '种草'),
            ),
            push=PushConfig(
                token=push_data.get('token', ''),
                enabled=push_data.get('enabled', True),
            ),
            storage=StorageConfig(
                chromadb_path=storage_data.get('chromadb_path', 'data/chromadb'),
                output_dir=storage_data.get('output_dir', 'output'),
            ),
            account=AccountConfig(
                name=account_data.get('name', 'AI技术前沿'),
                tone=account_data.get('tone', '专业且引人入胜'),
                niche=account_data.get('niche', 'AI技术'),
                min_length=account_data.get('min_length', 1500),
                max_length=account_data.get('max_length', 2500),
                max_title_length=account_data.get('max_title_length', 22),
            ),
            system=SystemConfig(
                log_level=system_data.get('log_level', 'INFO'),
            ),
            content=ContentConfig(
                banned_words=banned_words,
                ai_word_replacements=ai_replacements,
            ),
            config_source=source,
        )


@lru_cache
def get_settings() -> Settings:
    """
    获取配置单例

    优先级：
    1. config.yaml（推荐）
    2. .env（向下兼容）
    3. 默认值

    Returns:
        Settings: 配置实例

    Usage:
        from src.config import get_settings, settings

        # 方式一：通过函数获取
        config = get_settings()
        print(config.gemini.api_key)

        # 方式二：直接使用全局变量
        print(settings.gemini.api_key)
    """
    # 优先使用 config.yaml
    if CONFIG_YAML.exists():
        data = load_yaml_config()
        return Settings.from_dict(data, source="config.yaml")

    # 向下兼容 .env
    if ENV_FILE.exists():
        data = load_env_config()
        return Settings.from_dict(data, source=".env")

    # 使用默认值
    return Settings(config_source="默认配置")


def _is_valid_key(value: str, min_length: int = 10) -> bool:
    """
    检查配置值是否为有效的 Key（非占位符）

    Args:
        value: 配置值
        min_length: 最小有效长度

    Returns:
        bool: 是否为有效配置
    """
    if not value or not isinstance(value, str):
        return False

    value_lower = value.lower().strip()

    # 检查常见占位符模式
    placeholder_patterns = [
        'your_',           # your_api_key_here, your_token_here
        'xxx',             # xxx, xxxxxx
        'placeholder',     # placeholder
        'example',         # example_key
        'test_',           # test_key
        'demo_',           # demo_key
        'fill_',           # fill_in_here
        'replace_',        # replace_with_your_key
        '<',               # <your_key>
        '[',               # [your_key]
        '{',               # {your_key}
        'todo',            # TODO
        'fixme',           # FIXME
        'change_me',       # change_me
        'insert_',         # insert_your_key
        'put_',            # put_your_key_here
        'api_key_here',    # api_key_here
        'token_here',      # token_here
    ]

    for pattern in placeholder_patterns:
        if pattern in value_lower:
            return False

    # 长度检查（有效的 API Key 通常较长）
    if len(value.strip()) < min_length:
        return False

    return True


def get_config_status() -> dict:
    """
    获取配置状态信息（用于 CLI 显示）

    Returns:
        dict: 配置状态字典
    """
    s = get_settings()

    return {
        'config_source': s.config_source,
        'config_file': str(CONFIG_YAML) if CONFIG_YAML.exists() else (str(ENV_FILE) if ENV_FILE.exists() else '无'),
        'gemini': {
            'model': s.gemini.model,
            'api_key_configured': _is_valid_key(s.gemini.api_key, min_length=20),  # Gemini Key 较长
        },
        'github': {
            'token_configured': _is_valid_key(s.github.token, min_length=30),  # GitHub Token 较长
            'min_stars': s.github.min_stars,
        },
        'twitter': {
            'cookies_path': s.twitter.cookies_path,
            'cookies_exists': s.twitter.cookies_file.exists(),
        },
        'pushplus': {
            'token_configured': _is_valid_key(s.push.token, min_length=10),  # PushPlus Token 较短
            'enabled': s.push.enabled,
        },
        'account': {
            'name': s.account.name,
            'niche': s.account.niche,
        },
        'content': {
            'banned_words_count': len(s.content.banned_words),
            'ai_replacements_count': len(s.content.ai_word_replacements),
        },
    }


# 便捷访问 - 全局配置实例
settings = get_settings()
