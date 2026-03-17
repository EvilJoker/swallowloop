"""任务仓库接口"""

from abc import ABC, abstractmethod

from ..model import Task, TaskId


class TaskRepository(ABC):
    """
    任务仓库接口
    
    定义任务持久化的抽象操作
    """
    
    @abstractmethod
    def get(self, task_id: TaskId) -> Task | None:
        """根据ID获取任务"""
        pass
    
    @abstractmethod
    def get_by_issue(self, issue_number: int) -> Task | None:
        """根据Issue编号获取任务"""
        pass
    
    @abstractmethod
    def save(self, task: Task) -> None:
        """保存任务"""
        pass
    
    @abstractmethod
    def list_all(self) -> list[Task]:
        """列出所有任务"""
        pass
    
    @abstractmethod
    def list_active(self) -> list[Task]:
        """列出活跃任务"""
        pass
    
    @abstractmethod
    def list_completed(self) -> list[Task]:
        """列出已完成/已终止的任务"""
        pass
    
    @abstractmethod
    def delete(self, task_id: TaskId) -> bool:
        """删除任务"""
        pass