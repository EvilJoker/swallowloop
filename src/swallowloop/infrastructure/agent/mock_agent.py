"""Mock Agent - 用于测试环境"""

import asyncio
import logging
from typing import Any

from .base import BaseAgent, AgentResult

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
