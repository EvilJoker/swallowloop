"""工作空间仓库接口"""

from abc import ABC, abstractmethod
from typing import Protocol

from ..model import Workspace


class WorkspaceRepository(ABC):
    """
    工作空间仓库接口
    
    定义工作空间管理的抽象操作
    """
    
    @abstractmethod
    def get(self, issue_number: int) -> Workspace | None:
        """获取Issue的工作空间"""
        pass
    
    @abstractmethod
    def save(self, workspace: Workspace) -> None:
        """保存工作空间"""
        pass
    
    @abstractmethod
    def release(self, issue_number: int) -> bool:
        """释放工作空间"""
        pass
    
    @abstractmethod
    def list_active(self) -> list[Workspace]:
        """列出活跃工作空间"""
        pass
