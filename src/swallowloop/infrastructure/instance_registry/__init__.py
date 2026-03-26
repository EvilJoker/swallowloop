"""实例注册模块"""

MODULE_NAME = "infrastructure.instance_registry"

from .registry import InstanceRegistry, get_instance, register_instance, clear_instances

__all__ = [
    "MODULE_NAME",
    "InstanceRegistry",
    "get_instance",
    "register_instance",
    "clear_instances",
]
