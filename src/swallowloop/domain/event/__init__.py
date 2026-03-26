"""领域事件"""

MODULE_NAME = "domain.event"

from .base import DomainEvent

__all__ = [
    "MODULE_NAME",
    "DomainEvent",
]
