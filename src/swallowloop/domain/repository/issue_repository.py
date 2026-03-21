"""Issue 仓库接口"""

from abc import ABC, abstractmethod

from ..model import Issue, IssueId


class IssueRepository(ABC):
    """Issue 仓库接口"""

    @abstractmethod
    def get(self, issue_id: IssueId) -> Issue | None:
        """根据 ID 获取 Issue"""

    @abstractmethod
    def save(self, issue: Issue) -> None:
        """保存 Issue"""

    @abstractmethod
    def list_all(self) -> list[Issue]:
        """列出所有 Issue"""

    @abstractmethod
    def list_active(self) -> list[Issue]:
        """列出活跃 Issue"""

    @abstractmethod
    def delete(self, issue_id: IssueId) -> bool:
        """删除 Issue"""
