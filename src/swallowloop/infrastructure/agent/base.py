"""Agent 抽象基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...domain.model import Task, Workspace
    from ..llm.base import LLMProvider


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    message: str
    files_changed: list[str] = field(default_factory=list)
    output: str = ""


class Agent(ABC):
    """
    代码生成代理接口
    
    定义执行任务生成代码的抽象操作
    """
    
    @abstractmethod
    def execute(
        self,
        task: "Task",
        workspace_path: Path,
    ) -> ExecutionResult:
        """
        执行任务
        
        Args:
            task: 任务对象
            workspace_path: 工作空间路径
            
        Returns:
            ExecutionResult 执行结果
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """代理名称"""
        pass
    
    @staticmethod
    @abstractmethod
    def check_available() -> tuple[bool, str]:
        """检查代理是否可用"""
        pass
