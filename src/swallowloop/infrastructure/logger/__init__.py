"""日志模块"""

MODULE_NAME = "infrastructure.logger"

from .logger import setup_logging, get_logger, DailyRotatingFileHandler, ColoredFormatter

__all__ = [
    "MODULE_NAME",
    "setup_logging",
    "get_logger",
    "DailyRotatingFileHandler",
    "ColoredFormatter",
]
