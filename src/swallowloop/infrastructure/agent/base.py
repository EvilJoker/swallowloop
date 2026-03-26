"""Agent 接口定义"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class AgentResult:
    """Agent 执行结果"""
    success: bool
    output: str
    error: str | None = None


class BaseAgent(ABC):
    """Agent 基类"""

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
