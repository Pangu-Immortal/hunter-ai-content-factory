"""
Hunter AI 内容工厂 - 结构化日志模块

功能：
- 提供统一的日志接口
- 支持 Rich 终端美化输出
- 支持日志级别配置
- 各模块独立日志器

使用方法：
    from src.utils.logger import get_logger

    logger = get_logger("hunter.intel")
    logger.info("开始采集...")
    logger.error("采集失败", exc_info=True)
"""

import logging
from functools import lru_cache

from rich.console import Console
from rich.logging import RichHandler

from src.config import ROOT_DIR, settings

# 日志目录
LOGS_DIR = ROOT_DIR / "data" / "logs"


def setup_file_handler(logger: logging.Logger, log_file: str) -> None:
    """
    添加文件日志处理器

    Args:
        logger: 日志器实例
        log_file: 日志文件名
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = LOGS_DIR / log_file

    file_handler = logging.FileHandler(file_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(file_handler)


@lru_cache
def get_logger(
    name: str,
    level: str | None = None,
    log_to_file: bool = False,
) -> logging.Logger:
    """
    获取日志器实例

    Args:
        name: 日志器名称（如 "hunter.intel"）
        level: 日志级别（可选，默认从配置读取）
        log_to_file: 是否输出到文件

    Returns:
        logging.Logger: 日志器实例

    Example:
        logger = get_logger("hunter.intel")
        logger.info("开始采集 GitHub 项目")
        logger.warning("API 速率受限")
        logger.error("采集失败", exc_info=True)
    """
    logger = logging.getLogger(name)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # 设置日志级别
    log_level = level or settings.system.log_level
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Rich 终端输出
    rich_handler = RichHandler(
        console=Console(stderr=True),
        show_time=True,
        show_path=False,
        rich_tracebacks=True,
        tracebacks_show_locals=False,
    )
    rich_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(rich_handler)

    # 文件输出（可选）
    if log_to_file:
        module_name = name.split(".")[-1]
        setup_file_handler(logger, f"{module_name}.log")

    return logger


# ═══════════════════════════════════════════════════════════════════════════════
# 预定义的模块日志器
# ═══════════════════════════════════════════════════════════════════════════════


def get_intel_logger() -> logging.Logger:
    """获取情报模块日志器"""
    return get_logger("hunter.intel", log_to_file=True)


def get_factory_logger() -> logging.Logger:
    """获取工厂模块日志器"""
    return get_logger("hunter.factory", log_to_file=True)


def get_refiner_logger() -> logging.Logger:
    """获取精炼模块日志器"""
    return get_logger("hunter.refiner", log_to_file=True)


def get_config_logger() -> logging.Logger:
    """获取配置模块日志器"""
    return get_logger("hunter.config")


# ═══════════════════════════════════════════════════════════════════════════════
# 便捷日志函数
# ═══════════════════════════════════════════════════════════════════════════════

_default_logger = None


def _get_default_logger() -> logging.Logger:
    """获取默认日志器"""
    global _default_logger
    if _default_logger is None:
        _default_logger = get_logger("hunter")
    return _default_logger


def info(msg: str, *args, **kwargs):
    """记录 INFO 级别日志"""
    _get_default_logger().info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """记录 WARNING 级别日志"""
    _get_default_logger().warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """记录 ERROR 级别日志"""
    _get_default_logger().error(msg, *args, **kwargs)


def debug(msg: str, *args, **kwargs):
    """记录 DEBUG 级别日志"""
    _get_default_logger().debug(msg, *args, **kwargs)


# 模块测试
if __name__ == "__main__":
    # 测试日志输出
    logger = get_logger("hunter.test", level="DEBUG")

    logger.debug("这是 DEBUG 级别日志")
    logger.info("这是 INFO 级别日志")
    logger.warning("这是 WARNING 级别日志")
    logger.error("这是 ERROR 级别日志")

    try:
        raise ValueError("测试异常")
    except Exception:
        logger.exception("捕获到异常")
