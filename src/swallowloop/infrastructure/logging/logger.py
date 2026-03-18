"""日志配置模块

支持按天滚动的日志文件，输出到 .swallowloop/logs 目录
支持彩色终端输出，区分主进程和 Worker 进程
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional


# 日志格式（包含进程信息）
LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(processName)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 终端彩色输出
class ColoredFormatter(logging.Formatter):
    """彩色日志格式器"""
    
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
        "SpawnProcess": "\033[35m",    # 紫色 - Worker 进程
    }
    
    def format(self, record: logging.LogRecord) -> str:
        # 设置进程名称颜色
        process_name = record.processName
        color = self.PROCESS_COLORS.get(process_name, "")
        record.processName = f"{color}{process_name}{self.RESET}"
        
        # 设置级别颜色
        level_color = self.COLORS.get(record.levelname, "")
        record.levelname = f"{level_color}{record.levelname}{self.RESET}"
        
        return super().format(record)


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
    
    # 文件日志格式（不含颜色）
    file_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    
    # 文件处理器 - 按天滚动
    log_file = log_dir / "swallowloop.log"
    file_handler = TimedRotatingFileHandler(
        filename=str(log_file),
        when="midnight",       # 每天午夜滚动
        interval=1,            # 间隔 1 天
        backupCount=30,       # 保留 30 天的日志
        encoding="utf-8",
        utc=False,             # 使用本地时间
    )
    file_handler.suffix = "%Y-%m-%d"  # 滚动文件后缀格式
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # 控制台处理器（彩色输出）
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        console_formatter = ColoredFormatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        console_handler.setFormatter(console_formatter)
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
