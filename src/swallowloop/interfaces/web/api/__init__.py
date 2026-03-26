"""Web API 接口"""

MODULE_NAME = "interfaces.web.api"

from .issues import router, init_services

__all__ = [
    "MODULE_NAME",
    "router",
    "init_services",
]
