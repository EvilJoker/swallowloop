"""仓库接口"""

MODULE_NAME = "domain.repository"

from .workspace_repository import WorkspaceRepository
from .issue_repository import IssueRepository

__all__ = [
    "MODULE_NAME",
    "WorkspaceRepository",
    "IssueRepository",
]
