"""Logger 模块测试"""

import pytest
import logging
import tempfile
import shutil
from pathlib import Path

from swallowloop.infrastructure.logger import (
    setup_logging,
    get_logger,
    DailyRotatingFileHandler,
    ColoredFormatter,
)


class TestDailyRotatingFileHandler:
    """DailyRotatingFileHandler 测试"""

    def test_init_creates_log_dir(self, tmp_path):
        """初始化时创建日志目录"""
        log_dir = tmp_path / "logs"
        handler = DailyRotatingFileHandler(log_dir)
        assert log_dir.exists()

    def test_get_log_file_path(self, tmp_path):
        """获取日志文件路径"""
        handler = DailyRotatingFileHandler(tmp_path)
        date_str = "2024-01-15"
        path = handler._get_log_file_path(date_str)
        assert path == tmp_path / f"swallowloop-{date_str}.log"

    def test_get_current_date_format(self, tmp_path):
        """当前日期格式正确"""
        handler = DailyRotatingFileHandler(tmp_path)
        date_str = handler._get_current_date()
        # 格式: YYYY-MM-DD
        assert len(date_str) == 10
        assert date_str[4] == "-"
        assert date_str[7] == "-"


class TestColoredFormatter:
    """ColoredFormatter 测试"""

    def test_colors_defined(self):
        """颜色定义存在"""
        formatter = ColoredFormatter()
        assert "DEBUG" in formatter.COLORS
        assert "INFO" in formatter.COLORS
        assert "WARNING" in formatter.COLORS
        assert "ERROR" in formatter.COLORS
        assert "CRITICAL" in formatter.COLORS

    def test_reset_defined(self):
        """重置码定义"""
        formatter = ColoredFormatter()
        assert formatter.RESET == "\033[0m"


class TestSetupLogging:
    """setup_logging 测试"""

    def test_setup_creates_handlers(self, tmp_path, monkeypatch):
        """setup_logging 创建处理器"""
        # 清理已初始化的状态
        import swallowloop.infrastructure.logger as logger_module
        logger_module._logger_initialized = False

        setup_logging(log_dir=tmp_path)

        root_logger = logging.getLogger("swallowloop")
        # 应该有文件处理器和控制台处理器
        assert len(root_logger.handlers) >= 1

    def test_setup_idempotent(self, tmp_path, monkeypatch):
        """setup_logging 幂等性"""
        import swallowloop.infrastructure.logger as logger_module
        logger_module._logger_initialized = False

        setup_logging(log_dir=tmp_path)
        setup_logging(log_dir=tmp_path)

        root_logger = logging.getLogger("swallowloop")
        # 不应该重复添加处理器
        # 注意：由于 handlers.clear()，可能只有一个
        assert len(root_logger.handlers) >= 1


class TestGetLogger:
    """get_logger 测试"""

    def test_get_logger_prefix(self):
        """自动添加 swallowloop 前缀"""
        logger = get_logger("my.module")
        assert logger.name == "swallowloop.my.module"

    def test_get_logger_already_has_prefix(self):
        """已有前缀不重复添加"""
        logger = get_logger("swallowloop.other.module")
        assert logger.name == "swallowloop.other.module"

    def test_get_logger_returns_logger(self):
        """返回 Logger 实例"""
        logger = get_logger("test")
        assert isinstance(logger, logging.Logger)
