"""Dashboard 日志处理器 - 将日志发送到前端"""

import logging
from datetime import datetime
from typing import Callable, Optional


class DashboardLogHandler(logging.Handler):
    """
    自定义日志处理器，将日志发送到 Dashboard
    
    用于实时显示任务执行日志
    """
    
    def __init__(self):
        super().__init__()
        self._emit_callback: Optional[Callable] = None
        self._current_issue: Optional[int] = None
    
    def set_emit_callback(self, callback: Callable[[int, str, str, str], None]):
        """设置日志发送回调函数"""
        self._emit_callback = callback
    
    def set_current_issue(self, issue_number: Optional[int]):
        """设置当前处理的 Issue 编号"""
        self._current_issue = issue_number
    
    def emit(self, record: logging.LogRecord):
        """发送日志记录"""
        if self._emit_callback is None or self._current_issue is None:
            return
        
        try:
            message = self.format(record)
            level = record.levelname
            self._emit_callback(self._current_issue, level, message, "system")
        except Exception:
            self.handleError(record)


# 全局 Dashboard 日志处理器实例
_dashboard_handler: Optional[DashboardLogHandler] = None


def get_dashboard_handler() -> DashboardLogHandler:
    """获取全局 Dashboard 日志处理器"""
    global _dashboard_handler
    if _dashboard_handler is None:
        _dashboard_handler = DashboardLogHandler()
    return _dashboard_handler


def setup_dashboard_logging(issue_number: Optional[int] = None):
    """
    设置 Dashboard 日志
    
    Args:
        issue_number: 当前处理的 Issue 编号
    """
    handler = get_dashboard_handler()
    handler.set_current_issue(issue_number)
    
    # 添加到根日志器
    root_logger = logging.getLogger()
    if handler not in root_logger.handlers:
        root_logger.addHandler(handler)
