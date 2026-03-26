"""Web 接口层"""

MODULE_NAME = "interfaces.web"

from .issue_api import app, run_server

__all__ = [
    "MODULE_NAME",
    "app",
    "run_server",
]
