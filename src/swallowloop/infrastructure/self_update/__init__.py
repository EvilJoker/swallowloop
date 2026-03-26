"""自更新模块"""

MODULE_NAME = "infrastructure.self_update"

from .main import SelfUpdater

__all__ = ["MODULE_NAME", "SelfUpdater"]
