"""接口层 - 外部交互"""

MODULE_NAME = "interfaces"

from .web import app, run_server

__all__ = [
    "MODULE_NAME",
    "app",
    "run_server",
]
