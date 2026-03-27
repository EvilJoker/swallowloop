"""Mock Agent - 用于测试环境"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from .base import BaseAgent, AgentResult
from ...domain.model.workspace import Workspace

logger = logging.getLogger(__name__)


class MockAgent(BaseAgent):
    """
    Mock Agent - 模拟 Agent 执行

    等待指定时间后返回固定的成功结果，用于测试环境。
    """

    def __init__(self, delay_seconds: float = 5.0):
        """
        Args:
            delay_seconds: 模拟执行延迟（秒），默认 5 秒
        """
        self._delay_seconds = delay_seconds

    async def initialize(self) -> None:
        """Mock Agent 不需要初始化"""
        logger.info("MockAgent 初始化完成")

    async def prepare(self, issue_id: str, context: dict[str, Any]) -> Workspace:
        """
        MockAgent 准备：在本地创建工作空间

        Args:
            issue_id: Issue ID
            context: 上下文信息（包含 repo_url、branch、stage 等）

        Returns:
            Workspace: 工作空间信息
        """
        workspace_path = Path.home() / ".swallowloop" / "default" / str(issue_id) / "workspace"
        workspace_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"MockAgent 准备工作空间: {workspace_path}")

        return Workspace(
            id=issue_id,
            ready=True,  # MockAgent 直接就绪
            workspace_path=str(workspace_path),
            repo_url=context.get("repo_url", ""),
            branch=context.get("branch", issue_id),
            metadata={},
        )

    async def execute(self, task: str, context: dict[str, Any]) -> AgentResult:
        """
        模拟执行任务

        等待延迟时间后返回固定的成功结果。

        Args:
            task: 任务描述
            context: 上下文信息

        Returns:
            AgentResult: 固定的成功结果
        """
        logger.info(f"MockAgent 开始执行任务: {task[:50]}...")

        # 模拟执行延迟
        await asyncio.sleep(self._delay_seconds)

        # 返回固定的成功结果
        result = AgentResult(
            success=True,
            output=f"[MockAgent] 任务已完成\n\n输入任务: {task}\n\n阶段: {context.get('stage', 'unknown')}\nIssue: {context.get('issue_id', 'unknown')}",
            error=None,
        )

        logger.info(f"MockAgent 任务完成，耗时 {self._delay_seconds} 秒")
        return result
