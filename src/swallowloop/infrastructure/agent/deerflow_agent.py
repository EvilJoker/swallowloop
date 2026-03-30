"""DeerFlow Agent - 通过 HTTP API 与 DeerFlow 通信"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

import httpx

from .base import AgentResult, BaseAgent
from ...domain.model.workspace import Workspace

logger = logging.getLogger(__name__)


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
        """
        thread_id = issue_id  # 默认使用 issue_id
        client = self._create_client()

        try:
            async with client:
                # 创建 Thread - LangGraph API 端点: POST /threads
                response = await client.post(
                    f"{self._base_url}/threads",
                    json={"metadata": {"issue_id": issue_id}}
                )
                if response.status_code in [200, 201]:
                    result = response.json()
                    thread_id = result.get("thread_id", issue_id)
                    logger.info(f"DeerFlow Thread 创建成功: {thread_id}")
                else:
                    logger.warning(f"DeerFlow Thread 创建失败: {response.status_code} - {response.text}")
                    # 如果创建失败，使用 issue_id 作为 thread_id
        except Exception as e:
            logger.warning(f"DeerFlow Thread 创建异常: {e}")
            # 异常时也使用 issue_id 作为 thread_id

        # 计算工作空间路径
        # DeerFlow 目录: .deer-flow/threads/{thread_id}/user-data/workspace/
        workspace_path = (
            Path.home() / ".deer-flow" / "threads" / thread_id / "user-data" / "workspace"
        ).resolve()

        return Workspace(
            id=thread_id,
            ready=True,  # Thread 创建后就认为就绪
            workspace_path=str(workspace_path),
            repo_url=context.get("repo_url", ""),
            branch=context.get("branch", issue_id),
            metadata={},
        )

    async def _wait_for_run(self, client: httpx.AsyncClient, thread_id: str, run_id: str, timeout: float = 300.0) -> dict[str, Any]:
        """等待 Run 完成并返回结果"""
        start_time = time.monotonic()
        poll_interval = 2.0  # 每 2 秒轮询一次

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Run {run_id} 执行超时（{timeout}秒）")

            try:
                response = await client.get(f"{self._base_url}/threads/{thread_id}/runs/{run_id}")
                if response.status_code == 200:
                    run_data = response.json()
                    status = run_data.get("status", "")

                    if status == "success":
                        # 获取线程状态以获取结果
                        thread_response = await client.get(f"{self._base_url}/threads/{thread_id}")
                        if thread_response.status_code == 200:
                            thread_data = thread_response.json()
                            return thread_data
                        return run_data
                    elif status == "failed":
                        raise Exception(f"Run {run_id} 执行失败")
                    elif status == "error":
                        error_msg = run_data.get("error", {}).get("message", "未知错误")
                        raise Exception(f"Run {run_id} 错误: {error_msg}")

                    # 继续等待
                    logger.debug(f"Run {run_id} 状态: {status}，继续等待...")
                    await asyncio.sleep(poll_interval)
                else:
                    logger.warning(f"获取 Run 状态失败: {response.status_code}")
                    await asyncio.sleep(poll_interval)
            except Exception as e:
                if "执行失败" in str(e) or "错误" in str(e):
                    raise
                await asyncio.sleep(poll_interval)

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

        client = self._create_client()

        try:
            async with client:
                # 发送消息到 Thread - LangGraph API 端点: POST /threads/{thread_id}/runs
                # assistant_id 使用 "lead_agent"
                response = await client.post(
                    f"{self._base_url}/threads/{thread_id}/runs",
                    json={
                        "assistant_id": "lead_agent",
                        "input": {
                            "messages": [{"role": "user", "content": task}]
                        },
                        "stream_mode": "values"
                    },
                    timeout=300.0  # 5分钟超时
                )

                if response.status_code in [200, 201]:
                    run_data = response.json()
                    run_id = run_data.get("run_id")
                    logger.info(f"DeerFlow Run 已提交: {run_id}，等待执行完成...")

                    # 等待 Run 完成
                    try:
                        thread_data = await self._wait_for_run(client, thread_id, run_id)
                        # 从线程状态中提取 AI 回复
                        messages = thread_data.get("values", {}).get("messages", [])

                        # 找到所有消息，提取文本内容
                        # DeerFlow 的响应可能在 type=ai 或 type=tool 消息中
                        all_responses = []
                        for msg in messages:
                            msg_type = msg.get("type", "")
                            content = msg.get("content", "")
                            if not content:
                                continue

                            # 处理字符串内容
                            if isinstance(content, str):
                                if len(content) > 10:  # 过滤掉太短的内容
                                    all_responses.append(content)
                            elif isinstance(content, list):
                                # 处理嵌套的内容块
                                for item in content:
                                    if isinstance(item, dict):
                                        if item.get("type") == "text":
                                            text = item.get("text", "")
                                            if text and len(text) > 10:
                                                all_responses.append(text)
                                    elif isinstance(item, str) and len(item) > 10:
                                        all_responses.append(item)

                        # 使用最后的响应（通常是最终回答）
                        ai_response = ""
                        if all_responses:
                            ai_response = all_responses[-1]

                        if not ai_response:
                            ai_response = str(thread_data.get("values", {}))

                        return AgentResult(
                            success=True,
                            output=ai_response,
                            error=None
                        )
                    except TimeoutError as e:
                        logger.error(f"DeerFlow Run 超时: {e}")
                        return AgentResult(success=False, output="", error=str(e))
                    except Exception as e:
                        logger.error(f"DeerFlow Run 执行失败: {e}")
                        return AgentResult(success=False, output="", error=str(e))
                else:
                    error_msg = f"DeerFlow 返回错误: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return AgentResult(success=False, output="", error=error_msg)
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
                # LangGraph API 端点: DELETE /threads/{thread_id}
                response = await client.delete(f"{self._base_url}/threads/{thread_id}")
                if response.status_code in [200, 204, 404]:
                    logger.info(f"DeerFlow Thread 清理成功: {thread_id}")
                else:
                    logger.warning(f"DeerFlow Thread 清理失败: {response.status_code}")
        except Exception as e:
            logger.warning(f"DeerFlow Thread 清理失败: {e}")
