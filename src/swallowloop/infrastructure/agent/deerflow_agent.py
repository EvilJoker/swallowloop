"""DeerFlow Agent - 通过 HTTP API 与 DeerFlow 通信"""

import logging
from pathlib import Path
from typing import Any

import httpx

from .base import AgentResult, BaseAgent
from ...domain.model.workspace import Workspace

logger = logging.getLogger(__name__)


class DeerFlowAgent(BaseAgent):
    """DeerFlow Agent - 通过 HTTP API 与 DeerFlow 通信"""

    def __init__(self, base_url: str = "http://localhost:2026"):
        """
        Args:
            base_url: DeerFlow 服务地址（默认 http://localhost:2026）
        """
        self._base_url = base_url
        self._client = httpx.AsyncClient(timeout=60.0)

    async def initialize(self) -> None:
        """检查 DeerFlow 连接"""
        try:
            response = await self._client.get(f"{self._base_url}/health")
            if response.status_code == 200:
                logger.info("DeerFlow 连接正常")
            else:
                logger.warning(f"DeerFlow 返回异常状态: {response.status_code}")
        except Exception as e:
            logger.warning(f"DeerFlow 连接检查失败: {e}")

    async def prepare(self, issue_id: str, context: dict[str, Any]) -> Workspace:
        """
        创建 DeerFlow Thread，返回工作空间信息

        Args:
            issue_id: Issue ID（用作 thread_id）
            context: 上下文信息（包含 repo_url、branch、stage 等）

        Returns:
            Workspace: 工作空间信息
        """
        thread_id = issue_id  # 用 issue_id 作为 thread_id

        # 创建 Thread
        try:
            response = await self._client.post(
                f"{self._base_url}/api/langgraph/threads",
                json={"metadata": {"issue_id": issue_id}}
            )
            if response.status_code == 200:
                result = response.json()
                thread_id = result.get("thread_id", issue_id)
                logger.info(f"DeerFlow Thread 创建成功: {thread_id}")
            else:
                logger.warning(f"DeerFlow Thread 创建失败: {response.status_code}")
        except Exception as e:
            logger.warning(f"DeerFlow Thread 创建异常: {e}")

        # 计算工作空间路径
        # DeerFlow 目录: .deer-flow/threads/{thread_id}/user-data/workspace/
        workspace_path = (
            Path.home() / ".deer-flow" / "threads" / thread_id / "user-data" / "workspace"
        ).resolve()

        return Workspace(
            id=thread_id,
            ready=True,  # Thread 创建后就认为就绪，实际下载由 SwallowLoop 后续处理
            workspace_path=str(workspace_path),
            repo_url=context.get("repo_url", ""),
            branch=context.get("branch", issue_id),
            metadata={},
        )

    async def execute(self, task: str, context: dict[str, Any]) -> AgentResult:
        """
        执行任务

        Args:
            task: 任务描述
            context: 上下文信息（包含 thread_id、workspace_path 等）

        Returns:
            AgentResult: 执行结果
        """
        thread_id = context.get("thread_id")
        if not thread_id:
            return AgentResult(success=False, output="", error="thread_id required")

        try:
            # 发送消息到 Thread
            response = await self._client.post(
                f"{self._base_url}/api/langgraph/threads/{thread_id}/runs",
                json={
                    "input": {
                        "messages": [{"role": "user", "content": task}]
                    },
                    "stream_mode": ["values", "messages-tuple"]
                },
                timeout=300.0  # 5分钟超时
            )

            if response.status_code == 200:
                # 简化处理：返回成功
                return AgentResult(
                    success=True,
                    output=f"[DeerFlow] 任务已提交: {task[:50]}...",
                    error=None
                )
            else:
                return AgentResult(
                    success=False,
                    output="",
                    error=f"DeerFlow 返回错误: {response.status_code}"
                )
        except Exception as e:
            logger.error(f"DeerFlow 执行失败: {e}")
            return AgentResult(success=False, output="", error=str(e))

    async def cleanup(self, thread_id: str) -> None:
        """
        清理 Thread

        Args:
            thread_id: Thread ID
        """
        try:
            await self._client.delete(f"{self._base_url}/api/langgraph/threads/{thread_id}")
            logger.info(f"DeerFlow Thread 清理成功: {thread_id}")
        except Exception as e:
            logger.warning(f"DeerFlow Thread 清理失败: {e}")

    async def close(self) -> None:
        """关闭客户端"""
        await self._client.aclose()
