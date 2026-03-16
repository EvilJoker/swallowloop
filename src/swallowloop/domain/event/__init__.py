"""领域事件"""

from .base import DomainEvent
from .task_events import (
    TaskAssigned,
    TaskStarted,
    TaskSubmitted,
    TaskRevised,
    TaskCompleted,
    TaskAborted,
)

__all__ = [
    "DomainEvent",
    "TaskAssigned",
    "TaskStarted",
    "TaskSubmitted",
    "TaskRevised",
    "TaskCompleted",
    "TaskAborted",
]