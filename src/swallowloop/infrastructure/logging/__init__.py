"""日志模块"""

MODULE_NAME = "infrastructure.logging"

from .logger import setup_logging, get_logger

__all__ = ["MODULE_NAME", "setup_logging", "get_logger"]
