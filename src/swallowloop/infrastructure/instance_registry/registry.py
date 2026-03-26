"""全局实例注册表

提供简单的服务定位器模式，用于在模块间共享实例。
优先使用依赖注入，只有在无法注入时才使用此注册表。

使用方式：
    # main.py 启动时注册
    from swallowloop.infrastructure.instance_registry import register_instance
    register_instance("repository", repository)
    register_instance("executor", executor)

    # 其他模块获取
    from swallowloop.infrastructure.instance_registry import get_instance
    repository = get_instance("repository")
"""

from typing import Any


class InstanceRegistry:
    """全局实例注册表"""

    def __init__(self):
        self._instances: dict[str, Any] = {}

    def register(self, name: str, instance: Any) -> None:
        """注册实例

        Args:
            name: 实例名称
            instance: 实例对象
        """
        self._instances[name] = instance

    def get(self, name: str) -> Any:
        """获取实例

        Args:
            name: 实例名称

        Returns:
            注册的实例，不存在返回 None
        """
        return self._instances.get(name)

    def clear(self) -> None:
        """清除所有注册实例（主要用于测试）"""
        self._instances.clear()

    def list_all(self) -> list[str]:
        """列出所有注册的实例名称"""
        return list(self._instances.keys())


# 全局注册表实例
_registry = InstanceRegistry()


def register_instance(name: str, instance: Any) -> None:
    """注册全局实例"""
    _registry.register(name, instance)


def get_instance(name: str) -> Any:
    """获取全局实例"""
    return _registry.get(name)


def clear_instances() -> None:
    """清除所有全局实例"""
    _registry.clear()
