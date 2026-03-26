"""自更新模块"""

MODULE_NAME = "infrastructure.self_update"

from .self_updater import SelfUpdater

__all__ = ["MODULE_NAME", "SelfUpdater"]
