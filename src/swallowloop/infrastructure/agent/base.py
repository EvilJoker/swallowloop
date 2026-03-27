"""Agent 接口定义"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ...domain.model.workspace import Workspace


@dataclass
class AgentResult:
    """Agent 执行结果"""
    success: bool
    output: str
    error: str | None = None


class BaseAgent(ABC):
    """Agent 基类"""

    @abstractmethod
    async def prepare(self, issue_id: str, context: dict[str, Any]) -> Workspace:
        """
        准备工作空间，返回工作空间信息

        Args:
            issue_id: Issue ID
            context: 上下文信息（包含 repo_url、branch、stage 等）

        Returns:
            Workspace: 工作空间信息
        """
        pass

    @abstractmethod
    async def execute(self, task: str, context: dict[str, Any]) -> AgentResult:
        """
        执行任务

        Args:
            task: 任务描述
            context: 上下文信息（包含 issue、stage 等）

        Returns:
            AgentResult: 执行结果
        """
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """初始化 Agent"""
        pass
