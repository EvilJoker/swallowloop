"""Agent 接口定义"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from ...domain.model.workspace import Workspace


@dataclass
class AgentResult:
    """Agent 执行结果"""
    success: bool
    output: str
    error: str | None = None


@dataclass
class AgentStatus:
    """Agent 状态信息"""
    status: str = "offline"  # "online" | "offline"
    version: Optional[str] = None
    model_name: Optional[str] = None
    model_display_name: Optional[str] = None
    llm_used: int = 0
    llm_quota: int = 1500
    llm_next_refresh: Optional[str] = None
    base_url: str = ""
    active_threads: int = 0
    last_update: Optional[datetime] = field(default=None)


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

    @abstractmethod
    def get_status(self) -> AgentStatus:
        """
        获取缓存状态（同步，毫秒级）

        Returns:
            AgentStatus: 当前缓存的状态
        """
        pass

    @abstractmethod
    async def fetch_status(self) -> AgentStatus:
        """
        刷新状态（异步，可能有网络延迟）

        Returns:
            AgentStatus: 最新状态
        """
        pass

    @abstractmethod
    async def cleanup(self, thread_id: str, workspace_path: str | None = None) -> None:
        """
        清理 Thread 资源

        Args:
            thread_id: Thread ID
            workspace_path: 工作空间路径（可选，用于清理本地目录）
        """
        pass
