"""日志模块 - 支持按日期滚动的文件日志，支持彩色终端输出"""

import logging
import re
import sys
from datetime import datetime
from pathlib import Path

from ..constants import SENSITIVE_KEYS


class DailyRotatingFileHandler(logging.Handler):
    """
    按日期滚动的文件日志处理器
    
    每天创建一个新的日志文件，文件名格式: swallowloop-YYYY-MM-DD.log
    """
    
    def __init__(self, log_dir: Path):
        super().__init__()
        self._log_dir = log_dir
        self._current_date: str | None = None
        self._file_handler: logging.FileHandler | None = None
        self._ensure_log_dir()
    
    def _ensure_log_dir(self) -> None:
        """确保日志目录存在"""
        self._log_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_current_date(self) -> str:
        """获取当前日期字符串"""
        return datetime.now().strftime("%Y-%m-%d")
    
    def _get_log_file_path(self, date_str: str) -> Path:
        """获取指定日期的日志文件路径"""
        return self._log_dir / f"swallowloop-{date_str}.log"
    
    def _rotate_if_needed(self) -> None:
        """检查是否需要滚动日志文件"""
        current_date = self._get_current_date()
        
        if current_date != self._current_date:
            # 关闭旧的文件处理器
            if self._file_handler:
                self._file_handler.close()
            
            # 创建新的文件处理器
            log_file = self._get_log_file_path(current_date)
            self._file_handler = logging.FileHandler(log_file, encoding="utf-8")
            self._file_handler.setFormatter(self.formatter or self._create_default_formatter())
            self._current_date = current_date
    
    def _create_default_formatter(self) -> logging.Formatter:
        """创建默认日志格式"""
        return logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | [%(processName)s] %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    def emit(self, record: logging.LogRecord) -> None:
        """发送日志记录"""
        try:
            self._rotate_if_needed()
            if self._file_handler:
                self._file_handler.emit(record)
        except Exception:
            self.handleError(record)
    
    def close(self) -> None:
        """关闭处理器"""
        if self._file_handler:
            self._file_handler.close()
        super().close()


class ColoredFormatter(logging.Formatter):
    """彩色日志格式器（终端输出）"""
    
    COLORS = {
        "DEBUG": "\033[36m",     # 青色
        "INFO": "\033[32m",      # 绿色
        "WARNING": "\033[33m",   # 黄色
        "ERROR": "\033[31m",     # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"
    
    # 进程名称颜色
    PROCESS_COLORS = {
        "MainProcess": "\033[34m",     # 蓝色 - 主进程
    }
    
    def format(self, record: logging.LogRecord) -> str:
        # 设置进程名称颜色
        process_name = record.processName
        color = self.PROCESS_COLORS.get(process_name, "\033[35m")  # Worker 用紫色
        record.processName = f"{color}{process_name}{self.RESET}"
        
        # 设置级别颜色
        level_color = self.COLORS.get(record.levelname, "")
        record.levelname = f"{level_color}{record.levelname}{self.RESET}"
        
        return super().format(record)


# 全局日志配置
_logger_initialized = False


def setup_logging(log_dir: Path | None = None, level: int = logging.INFO) -> None:
    """
    配置全局日志
    
    Args:
        log_dir: 日志目录路径，默认为 ~/.swallowloop/logs
        level: 日志级别，默认 INFO
    """
    global _logger_initialized
    
    if _logger_initialized:
        return
    
    if log_dir is None:
        log_dir = Path.home() / ".swallowloop" / "logs"
    
    # 创建根日志器
    root_logger = logging.getLogger("swallowloop")
    root_logger.setLevel(level)
    
    # 移除已有的处理器
    root_logger.handlers.clear()
    
    # 格式：包含进程信息
    log_fmt = "%(asctime)s | %(levelname)-8s | [%(processName)s] %(name)s | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"
    
    # 文件日志格式（无颜色）
    file_formatter = logging.Formatter(fmt=log_fmt, datefmt=date_fmt)
    
    # 添加文件处理器（按日期滚动）
    file_handler = DailyRotatingFileHandler(log_dir)
    file_handler.setLevel(level)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # 终端处理器（彩色输出）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = ColoredFormatter(fmt=log_fmt, datefmt=date_fmt)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    _logger_initialized = True


def get_logger(name: str) -> logging.Logger:
    """
    获取日志器

    Args:
        name: 日志器名称，通常使用 __name__

    Returns:
        配置好的日志器实例
    """
    if not name.startswith("swallowloop"):
        name = f"swallowloop.{name}"
    return logging.getLogger(name)


def sanitize_log_message(msg: str) -> str:
    """
    脱敏日志消息，隐藏敏感信息

    Args:
        msg: 原始日志消息

    Returns:
        脱敏后的消息
    """
    result = msg
    for key in SENSITIVE_KEYS:
        # 匹配各种敏感格式: api_key=xxx, "api_key": "xxx", apiKey: xxx
        patterns = [
            rf'{key}=["\']?[^"\'\s]+["\']?',
            rf'"{key}":\s*"[^"]+"',
            rf'"{key}":\s*\'[^\']+\'',
        ]
        for pattern in patterns:
            result = re.sub(pattern, f'{key}=[REDACTED]', result, flags=re.IGNORECASE)
    return result
