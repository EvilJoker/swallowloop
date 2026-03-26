"""数据传输对象"""

MODULE_NAME = "application.dto"

from .issue_dto import IssueDTO, WorkspaceDTO

__all__ = [
    "MODULE_NAME",
    "IssueDTO",
    "WorkspaceDTO",
]
