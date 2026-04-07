"""工作空间仓库接口"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

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
    
    @abstractmethod
    def list_expired(self, days: int = 7) -> list[Workspace]:
        """列出过期的工作空间（已完成/已终止超过指定天数）"""
        pass
    
    @abstractmethod
    def delete(self, workspace_id: str) -> bool:
        """删除工作空间记录"""
        pass
