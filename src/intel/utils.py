"""
Hunter AI 内容工厂 - 情报模块公共工具

功能：
- HTTP 客户端创建（带重试机制）
- 内容去重与存储
- 报告生成与推送
- 统一重试装饰器（基于 tenacity）

使用方法：
    from src.intel.utils import retry_on_error, retry_async

    @retry_on_error(max_attempts=3)
    def my_function():
        ...

    @retry_async(max_attempts=5, min_wait=1, max_wait=30)
    async def my_async_function():
        ...

GitHub: https://github.com/Pangu-Immortal/hunter-ai-content-factory
Author: Pangu-Immortal
"""

import datetime
import hashlib
import logging
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import ParamSpec, TypeVar

import chromadb
import httpx
from rich.console import Console
from tenacity import (
    RetryError,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import settings

# 终端输出美化
console = Console()

# 日志配置（用于重试日志）
logger = logging.getLogger("hunter.intel")

# 类型变量（用于泛型装饰器）
P = ParamSpec("P")
T = TypeVar("T")


# ═══════════════════════════════════════════════════════════════════════════════
# 重试装饰器（基于 tenacity）
# ═══════════════════════════════════════════════════════════════════════════════

# 可重试的异常类型
RETRYABLE_EXCEPTIONS = (
    httpx.TimeoutException,  # 超时
    httpx.ConnectError,  # 连接错误
    httpx.ReadError,  # 读取错误
    httpx.WriteError,  # 写入错误
    httpx.PoolTimeout,  # 连接池超时
    ConnectionError,  # 通用连接错误
    TimeoutError,  # 通用超时
)


def retry_on_error(
    max_attempts: int = 3,
    min_wait: float = 1,
    max_wait: float = 10,
    exceptions: tuple = RETRYABLE_EXCEPTIONS,
):
    """
    同步函数重试装饰器

    使用 tenacity 实现指数退避重试，适用于 API 调用等网络操作

    Args:
        max_attempts: 最大重试次数（默认 3 次）
        min_wait: 最小等待时间（秒，默认 1 秒）
        max_wait: 最大等待时间（秒，默认 10 秒）
        exceptions: 可重试的异常类型元组

    Returns:
        装饰器函数

    示例:
        @retry_on_error(max_attempts=5)
        def call_api():
            response = httpx.get("https://api.example.com")
            return response.json()
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


def retry_async(
    max_attempts: int = 3,
    min_wait: float = 1,
    max_wait: float = 10,
    exceptions: tuple = RETRYABLE_EXCEPTIONS,
):
    """
    异步函数重试装饰器

    使用 tenacity 实现指数退避重试，适用于异步 API 调用

    Args:
        max_attempts: 最大重试次数（默认 3 次）
        min_wait: 最小等待时间（秒，默认 1 秒）
        max_wait: 最大等待时间（秒，默认 10 秒）
        exceptions: 可重试的异常类型元组

    Returns:
        装饰器函数

    示例:
        @retry_async(max_attempts=5, min_wait=2, max_wait=30)
        async def call_async_api():
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.example.com")
                return response.json()
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


def safe_retry[**P, T](func: Callable[P, T]) -> Callable[P, T | None]:
    """
    安全重试包装器（不抛出异常，失败返回 None）

    适用于非关键操作，失败时静默处理

    Args:
        func: 要包装的函数

    Returns:
        包装后的函数

    示例:
        @safe_retry
        @retry_on_error(max_attempts=3)
        def optional_api_call():
            ...
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
        try:
            return func(*args, **kwargs)
        except (RetryError, Exception) as e:
            console.print(f"[yellow]⚠️ 操作失败（已重试）: {e}[/yellow]")
            return None

    return wrapper


def create_http_client(timeout: float = 30.0, retries: int = 3) -> httpx.Client:
    """
    创建 HTTP 客户端（带重试机制，无代理）

    Args:
        timeout: 请求超时时间（秒）
        retries: 重试次数

    Returns:
        httpx.Client: HTTP 客户端实例
    """
    transport = httpx.HTTPTransport(retries=retries)  # 重试机制
    return httpx.Client(
        timeout=timeout,
        transport=transport,
        follow_redirects=True,  # 自动跟随重定向
    )


def create_async_http_client(timeout: float = 30.0, retries: int = 3) -> httpx.AsyncClient:
    """
    创建异步 HTTP 客户端

    Args:
        timeout: 请求超时时间（秒）
        retries: 重试次数

    Returns:
        httpx.AsyncClient: 异步 HTTP 客户端实例
    """
    transport = httpx.AsyncHTTPTransport(retries=retries)  # 异步重试机制
    return httpx.AsyncClient(
        timeout=timeout,
        transport=transport,
        follow_redirects=True,
    )


def get_chromadb_client() -> chromadb.PersistentClient:
    """
    获取 ChromaDB 客户端

    Returns:
        chromadb.PersistentClient: ChromaDB 持久化客户端
    """
    db_path = settings.storage.chromadb_dir  # 从配置获取存储路径
    db_path.mkdir(parents=True, exist_ok=True)  # 确保目录存在
    return chromadb.PersistentClient(path=str(db_path))


def generate_content_id(source: str, content: str, author: str = "") -> str:
    """
    生成内容唯一标识（基于内容哈希去重）

    Args:
        source: 来源平台（如 GitHub、Twitter）
        content: 内容文本
        author: 作者名称

    Returns:
        str: 唯一标识 ID
    """
    fingerprint = hashlib.md5(content.encode("utf-8")).hexdigest()  # 内容指纹
    return f"{source}_{author}_{fingerprint}"


@retry_on_error(max_attempts=3, min_wait=2, max_wait=15)
def push_to_wechat(title: str, content: str, template: str = "markdown") -> bool:
    """
    通过 PushPlus 推送消息到微信

    自带重试机制（3 次重试，指数退避）

    Args:
        title: 消息标题
        content: 消息内容（支持 Markdown）
        template: 模板类型（markdown/html/txt）

    Returns:
        bool: 推送是否成功
    """
    if not settings.push.token:  # 检查 Token 是否配置
        console.print("[yellow]⚠️ PushPlus Token 未配置，跳过推送[/yellow]")
        return False

    try:
        with create_http_client(timeout=15.0) as client:
            response = client.post(
                "https://www.pushplus.plus/send",  # PushPlus API
                json={
                    "token": settings.push.token,
                    "title": title[:100],  # 标题限制 100 字符
                    "content": content,
                    "template": template,
                },
            )
            result = response.json()

            if result.get("code") == 200:  # 推送成功
                console.print(f"[green]📨 推送成功！消息ID: {result.get('data')}[/green]")
                return True
            else:
                console.print(f"[red]❌ 推送失败: {result.get('msg')}[/red]")
                return False

    except Exception as e:
        console.print(f"[red]❌ 推送出错: {e}[/red]")
        return False


def get_output_path(filename: str, subdir: str = "reports") -> Path:
    """
    获取输出文件路径（旧版兼容）

    Args:
        filename: 文件名
        subdir: 子目录（reports/articles/covers）

    Returns:
        Path: 完整文件路径
    """
    output_dir = settings.storage.output_path / subdir  # 输出目录
    output_dir.mkdir(parents=True, exist_ok=True)  # 确保目录存在
    return output_dir / filename


def get_dated_output_path(filename: str, subdir: str = "reports", date_str: str = None) -> Path:
    """
    获取按日期组织的输出文件路径

    目录结构: output/2026-01-22/reports/filename

    Args:
        filename: 文件名
        subdir: 子目录类型（reports/articles/covers）
        date_str: 日期字符串（默认今天）

    Returns:
        Path: 完整文件路径
    """
    if date_str is None:
        date_str = get_today_str()

    # 构建路径: output/日期/子目录/
    output_dir = settings.storage.output_path / date_str / subdir
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / filename


def create_article_dir(article_title: str, date_str: str = None) -> Path:
    """
    创建文章专属目录（按日期/文章名组织）

    目录结构：output/2026-01-22/文章标题/
    每篇文章的所有相关文件（文章内容、封面图等）都存储在同一目录

    Args:
        article_title: 文章标题（会自动处理特殊字符）
        date_str: 日期字符串（默认今天）

    Returns:
        Path: 文章目录路径

    示例:
        >>> article_dir = create_article_dir("这3个YYDS开源AI项目绝了")
        >>> # 返回: output/2026-01-22/这3个YYDS开源AI项目绝了/
    """
    import re

    if date_str is None:
        date_str = get_today_str()

    # 清理文章标题中的特殊字符（保留中文、英文、数字）
    safe_title = re.sub(r'[<>:"/\\|?*\n\r\t]', "", article_title)  # 移除文件名非法字符
    safe_title = safe_title.strip()[:50]  # 限制长度，避免路径过长
    if not safe_title:
        safe_title = "untitled"

    # 构建目录路径: output/日期/文章标题/
    article_dir = settings.storage.output_path / date_str / safe_title
    article_dir.mkdir(parents=True, exist_ok=True)

    return article_dir


def get_article_file_path(article_dir: Path, filename: str) -> Path:
    """
    获取文章目录内的文件路径

    Args:
        article_dir: 文章目录（由 create_article_dir 返回）
        filename: 文件名

    Returns:
        Path: 完整文件路径
    """
    return article_dir / filename


def get_today_str() -> str:
    """
    获取今日日期字符串

    Returns:
        str: 格式化日期（如 2026-01-22）
    """
    return datetime.date.today().strftime("%Y-%m-%d")


async def call_with_retry(
    func: Callable, *args, max_attempts: int = 3, min_wait: float = 1, max_wait: float = 10, **kwargs
):
    """
    带重试的异步函数调用

    使用 tenacity 实现指数退避重试

    Args:
        func: 要调用的异步函数
        *args: 位置参数
        max_attempts: 最大重试次数
        min_wait: 最小等待时间（秒）
        max_wait: 最大等待时间（秒）
        **kwargs: 关键字参数

    Returns:
        函数返回值

    示例:
        result = await call_with_retry(fetch_data, url, max_attempts=5)
    """

    @retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _call():
        return await func(*args, **kwargs)

    return await _call()
