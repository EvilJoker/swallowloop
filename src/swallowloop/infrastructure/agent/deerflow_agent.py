"""DeerFlow Agent - 通过 HTTP API 与 DeerFlow 通信"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx

from .base import AgentResult, BaseAgent
from ...domain.model.workspace import Workspace

logger = logging.getLogger(__name__)

# 轮询配置
POLL_INTERVAL_SECONDS = 20  # 轮询间隔
MAX_EXECUTE_TIMEOUT_SECONDS = 1800  # 最大执行时间 30 分钟


class DeerFlowAgent(BaseAgent):
    """DeerFlow Agent - 通过 HTTP API 与 DeerFlow 通信"""

    def __init__(self, base_url: str = "http://localhost:2024"):
        """
        Args:
            base_url: DeerFlow LangGraph API 地址（默认 http://localhost:2024）
        """
        self._base_url = base_url

    def _create_client(self) -> httpx.AsyncClient:
        """创建 HTTP 客户端（每次调用创建新实例，避免 event loop 问题）"""
        return httpx.AsyncClient(timeout=300.0)

    async def initialize(self) -> None:
        """检查 DeerFlow 连接"""
        try:
            client = self._create_client()
            async with client:
                response = await client.get(f"{self._base_url}/threads")
                logger.info(f"DeerFlow 连接检查完成: {response.status_code}")
        except Exception as e:
            logger.warning(f"DeerFlow 连接检查失败: {e}")

    async def prepare(self, issue_id: str, context: dict[str, Any]) -> Workspace:
        """
        创建 DeerFlow Thread，返回工作空间信息

        Args:
            issue_id: Issue ID
            context: 上下文信息（包含 repo_url、branch、stage 等）

        Returns:
            Workspace: 工作空间信息

        Raises:
            Exception: 创建 Thread 失败时抛出
        """
        client = self._create_client()
        thread_id = None
        last_error = None

        # 重试 2 次创建 Thread
        for attempt in range(2):
            try:
                async with client:
                    response = await client.post(
                        f"{self._base_url}/threads",
                        json={"metadata": {"issue_id": issue_id}}
                    )
                    if response.status_code in [200, 201]:
                        result = response.json()
                        thread_id = result.get("thread_id")
                        logger.info(f"DeerFlow Thread 创建成功: {thread_id}")
                        break
                    else:
                        last_error = f"HTTP {response.status_code}: {response.text}"
                        logger.warning(f"DeerFlow Thread 创建失败（尝试 {attempt + 1}/2）: {last_error}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"DeerFlow Thread 创建异常（尝试 {attempt + 1}/2）: {e}")

        if not thread_id:
            raise Exception(f"创建 DeerFlow Thread 失败: {last_error}")

        # 计算工作空间路径
        # 实际路径: ~/.deer-flow/threads/{thread_id}/user-data/workspace/
        workspace_path = (
            Path.home() / ".deer-flow" / "threads" / thread_id / "user-data" / "workspace"
        ).resolve()

        # 确保目录存在
        workspace_path.mkdir(parents=True, exist_ok=True)

        return Workspace(
            id=thread_id,
            ready=True,
            workspace_path=str(workspace_path),
            repo_url=context.get("repo_url", ""),
            branch=context.get("branch", issue_id),
            metadata={},
        )

    async def _wait_for_result(self, result_file: str, timeout: float = MAX_EXECUTE_TIMEOUT_SECONDS) -> dict[str, Any] | None:
        """
        轮询等待 result.json 文件生成

        Args:
            result_file: result.json 文件路径
            timeout: 超时时间（秒）

        Returns:
            result.json 内容，解析后的 dict；或 None（超时或错误）
        """
        start_time = time.monotonic()
        poll_interval = POLL_INTERVAL_SECONDS

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > timeout:
                logger.error(f"等待 result.json 超时（{timeout}秒）: {result_file}")
                return None

            if os.path.exists(result_file):
                try:
                    with open(result_file, "r", encoding="utf-8") as f:
                        result = json.load(f)
                    logger.info(f"读取 result.json 成功: {result_file}")
                    return result
                except Exception as e:
                    logger.error(f"读取 result.json 失败: {e}")
                    return None

            logger.debug(f"result.json 尚未生成，继续等待...（已等待 {elapsed:.0f}秒）")
            await asyncio.sleep(poll_interval)

    async def execute(self, task: str, context: dict[str, Any]) -> AgentResult:
        """
        执行任务 - 发送消息给 DeerFlow Thread 并轮询 result.json

        Args:
            task: 任务指令（如 "请读取并执行..."）
            context: {
                "thread_id": "UUID",
                "stage_file": "/path/to/1-prepare.md",
                "result_file": "/path/to/1-prepare-result.json"
            }

        Returns:
            AgentResult: 执行结果
        """
        thread_id = context.get("thread_id")
        stage_file = context.get("stage_file", "")
        result_file = context.get("result_file", "")

        if not thread_id:
            return AgentResult(success=False, output="", error="thread_id required")

        if not stage_file or not result_file:
            return AgentResult(success=False, output="", error="stage_file 和 result_file 必须提供")

        client = self._create_client()

        try:
            async with client:
                # 发送消息到 Thread
                response = await client.post(
                    f"{self._base_url}/threads/{thread_id}/runs",
                    json={
                        "assistant_id": "lead_agent",
                        "input": {
                            "messages": [{"role": "user", "content": task}]
                        },
                        "stream_mode": "values"
                    },
                    timeout=300.0
                )

                if response.status_code not in [200, 201]:
                    error_msg = f"DeerFlow 返回错误: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return AgentResult(success=False, output="", error=error_msg)

                run_data = response.json()
                run_id = run_data.get("run_id")
                logger.info(f"DeerFlow Run 已提交: {run_id}，等待执行完成...")

                # 轮询等待 result.json
                result_data = await self._wait_for_result(result_file)

                if result_data is None:
                    return AgentResult(
                        success=False,
                        output="",
                        error=f"执行超时或读取 result.json 失败: {result_file}"
                    )

                # 解析 result.json
                status = result_data.get("status", "unknown")
                output = result_data.get("output", "")
                error = result_data.get("error", "")

                if status == "success":
                    return AgentResult(
                        success=True,
                        output=output,
                        error=None
                    )
                else:
                    return AgentResult(
                        success=False,
                        output=output,
                        error=error or "执行失败"
                    )

        except httpx.TimeoutException:
            logger.error("DeerFlow 请求超时")
            return AgentResult(success=False, output="", error="请求超时（5分钟）")
        except Exception as e:
            logger.error(f"DeerFlow 执行失败: {e}")
            return AgentResult(success=False, output="", error=str(e))

    async def cleanup(self, thread_id: str) -> None:
        """
        清理 Thread

        Args:
            thread_id: Thread ID
        """
        client = self._create_client()
        try:
            async with client:
                response = await client.delete(f"{self._base_url}/threads/{thread_id}")
                if response.status_code in [200, 204, 404]:
                    logger.info(f"DeerFlow Thread 清理成功: {thread_id}")
                else:
                    logger.warning(f"DeerFlow Thread 清理失败: {response.status_code}")
        except Exception as e:
            logger.warning(f"DeerFlow Thread 清理失败: {e}")
