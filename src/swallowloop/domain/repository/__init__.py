"""仓库接口"""

from .task_repository import TaskRepository
from .workspace_repository import WorkspaceRepository

__all__ = [
    "TaskRepository",
    "WorkspaceRepository",
]
