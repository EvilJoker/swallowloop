"""日志配置模块

支持按天滚动的日志文件，输出到 .swallowloop/logs 目录
"""

import logging
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional


# 日志格式
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    log_dir: Optional[Path] = None,
    log_level: str = "INFO",
    console_output: bool = True,
) -> None:
    """
    配置日志系统
    
    Args:
        log_dir: 日志目录，默认为 ~/.swallowloop/logs
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console_output: 是否同时输出到控制台
    """
    # 确定日志目录
    if log_dir is None:
        log_dir = Path.home() / ".swallowloop" / "logs"
    
    # 确保目录存在
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 获取根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # 清除已有处理器
    root_logger.handlers.clear()
    
    # 创建格式器
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    
    # 文件处理器 - 按天滚动
    log_file = log_dir / "swallowloop.log"
    file_handler = TimedRotatingFileHandler(
        filename=str(log_file),
        when="midnight",       # 每天午夜滚动
        interval=1,            # 间隔 1 天
        backupCount=30,        # 保留 30 天的日志
        encoding="utf-8",
        utc=False,             # 使用本地时间
    )
    file_handler.suffix = "%Y-%m-%d"  # 滚动文件后缀格式
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    获取日志器
    
    Args:
        name: 日志器名称，通常使用 __name__
        
    Returns:
        配置好的 Logger 实例
    """
    return logging.getLogger(name)
