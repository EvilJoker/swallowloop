"""仓库接口"""

from .workspace_repository import WorkspaceRepository
from .issue_repository import IssueRepository

__all__ = [
    "WorkspaceRepository",
    "IssueRepository",
]
