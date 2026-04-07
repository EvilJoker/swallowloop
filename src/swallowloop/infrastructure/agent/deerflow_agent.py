"""DeerFlow Agent - 通过 HTTP API 与 DeerFlow 通信"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx

from .base import AgentResult, AgentStatus, BaseAgent
from ...domain.model.workspace import Workspace
from ...infrastructure.deerflow import DeerFlowClient
from ...infrastructure.llm import get_llm_instance
from ..constants import (
    DEFAULT_DEERFLOW_BASE_URL,
    HttpTimeout,
    POLL_INTERVAL_SECONDS,
    MAX_EXECUTE_TIMEOUT_SECONDS,
)
from ..logger import sanitize_log_message

logger = logging.getLogger(__name__)


class DeerFlowAgent(BaseAgent):
    """DeerFlow Agent - 通过 HTTP API 与 DeerFlow 通信"""

    def __init__(self, base_url: str = DEFAULT_DEERFLOW_BASE_URL):
        """
        Args:
            base_url: DeerFlow LangGraph API 地址（默认 http://localhost:2026）
        """
        self._base_url = base_url
        self._cleanup_client = DeerFlowClient(base_url=base_url)
        self._status = AgentStatus(
            status="offline",
            version=None,
            model_name=None,
            model_display_name=None,
            llm_used=0,
            llm_quota=1500,
            llm_next_refresh=None,
            base_url=base_url,
            active_threads=0,
            last_update=None,
        )

    def _create_client(self) -> httpx.Client:
        """创建 HTTP 客户端（同步，每次调用创建新实例）"""
        return httpx.Client(timeout=300.0)

    def _create_async_client(self) -> httpx.AsyncClient:
        """创建异步 HTTP 客户端"""
        return httpx.AsyncClient(timeout=300.0)

    async def initialize(self) -> None:
        """检查 DeerFlow 连接"""
        try:
            async with self._create_async_client() as client:
                response = await client.get(f"{self._base_url}/api/threads")
                logger.info(f"DeerFlow 连接检查完成: {response.status_code}")
        except Exception as e:
            logger.warning(f"DeerFlow 连接检查失败: {e}")

    def get_status(self) -> AgentStatus:
        """获取缓存状态（同步，毫秒级）"""
        return self._status

    async def fetch_status(self) -> AgentStatus:
        """刷新状态（异步，调用 DeerFlow API + LLM API）"""
        # 检查 DeerFlow 服务状态
        is_online, version = await self._check_deerflow_health()
        model_name, model_display_name = await self._get_deerflow_model()

        # 获取 LLM 用量
        llm_used = 0
        llm_quota = 1500
        llm_next_refresh: Optional[str] = None
        llm = get_llm_instance()
        if llm:
            usage = await llm.fetch_usage()
            if usage:
                llm_used = usage.used
                llm_quota = usage.quota
                llm_next_refresh = usage.next_refresh.isoformat() if usage.next_refresh else None

        # 更新缓存
        self._status = AgentStatus(
            status="online" if is_online else "offline",
            version=version,
            model_name=model_name,
            model_display_name=model_display_name,
            llm_used=llm_used,
            llm_quota=llm_quota,
            llm_next_refresh=llm_next_refresh,
            base_url=self._base_url,
            active_threads=self._status.active_threads,  # TODO: 从 DeerFlow 获取真实数量
            last_update=datetime.now(),
        )
        return self._status

    async def _check_deerflow_health(self) -> tuple[bool, Optional[str]]:
        """检查 DeerFlow 服务状态"""
        try:
            async with httpx.AsyncClient(timeout=HttpTimeout.HEALTH_CHECK) as client:
                response = await client.get(f"{self._base_url}/api/langgraph/info")
                if response.status_code == 200:
                    data = response.json()
                    return True, data.get("version")
                return False, None
        except Exception:
            return False, None

    async def _get_deerflow_model(self) -> tuple[Optional[str], Optional[str]]:
        """获取 DeerFlow 当前使用的模型"""
        try:
            async with httpx.AsyncClient(timeout=HttpTimeout.HEALTH_CHECK) as client:
                response = await client.get(f"{self._base_url}/api/models")
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    if models:
                        model = models[0]
                        return model.get("model"), model.get("display_name")
                return None, None
        except Exception:
            return None, None

    def prepare(self, issue_id: str, context: dict[str, Any]) -> Workspace:
        """
        创建 DeerFlow Thread，返回工作空间信息（同步）

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
                with client:
                    response = client.post(
                        f"{self._base_url}/api/threads",
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
        执行任务 - 发送消息给 DeerFlow Thread 并获取响应结果

        Args:
            task: 任务指令（如 "请读取并执行..."）
            context: {
                "thread_id": "UUID",
                "stage_file": "/path/to/1-prepare.md"（可选，仅用于兼容性）,
                "result_file": "/path/to/1-prepare-result.json"（可选，仅用于兼容性）
            }

        Returns:
            AgentResult: 执行结果
        """
        thread_id = context.get("thread_id")

        if not thread_id:
            return AgentResult(success=False, output="", error="thread_id required")

        try:
            async with self._create_async_client() as client:
                # 发送消息到 Thread
                response = await client.post(
                    f"{self._base_url}/api/threads/{thread_id}/runs",
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

                # 等待 run 完成（轮询 status）
                output = await self._wait_for_run_complete(client, thread_id, run_id)

                if output is None:
                    return AgentResult(
                        success=False,
                        output="",
                        error="执行超时或 DeerFlow 执行失败"
                    )

                logger.info(f"DeerFlow 执行完成，获取到 {len(output)} 字符的输出")
                return AgentResult(
                    success=True,
                    output=output,
                    error=None
                )

        except httpx.TimeoutException:
            logger.error("DeerFlow 请求超时")
            return AgentResult(success=False, output="", error="请求超时（5分钟）")
        except Exception as e:
            logger.error(f"DeerFlow 执行失败: {e}")
            return AgentResult(success=False, output="", error=str(e))

    async def _wait_for_run_complete(self, client: httpx.AsyncClient, thread_id: str, run_id: str) -> str | None:
        """轮询等待 DeerFlow Run 完成，从响应中提取输出"""
        timeout = 300.0  # 5分钟超时
        start_time = time.monotonic()
        poll_interval = POLL_INTERVAL_SECONDS

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > timeout:
                logger.error(f"等待 DeerFlow Run 超时（{timeout}秒）")
                return None

            try:
                # 获取 run 状态
                status_response = await client.get(
                    f"{self._base_url}/api/threads/{thread_id}/runs/{run_id}",
                    timeout=30.0
                )

                if status_response.status_code != 200:
                    logger.warning(f"获取 Run 状态失败: {status_response.status_code}")
                    await asyncio.sleep(poll_interval)
                    continue

                run_status = status_response.json()
                status = run_status.get("status", "")

                if status in ["completed", "success"]:
                    # Run 完成，从 thread 的 values.messages 中提取最终输出
                    thread_response = await client.get(
                        f"{self._base_url}/api/threads/{thread_id}",
                        timeout=30.0
                    )

                    if thread_response.status_code == 200:
                        thread_data = thread_response.json()
                        # DeerFlow 返回结果在 values.messages 中
                        values = thread_data.get("values", {})
                        if isinstance(values, dict):
                            messages = values.get("messages", [])
                        else:
                            messages = []

                        # 从 messages 中找到 AI 的最后一条有效回复
                        for msg in reversed(messages):
                            msg_type = msg.get("type", "")
                            content = msg.get("content", "")

                            # 跳过 tool 调用类型的消息
                            if msg_type in ["tool", "stop"]:
                                continue

                            # 跳过 thinking 类型消息（显式的 thinking 消息）
                            if msg_type == "thinking":
                                continue

                            # 处理 content 可能是字符串或数组的情况
                            if isinstance(content, str):
                                output = content.strip()
                            elif isinstance(content, list):
                                # content 是片段数组，拼接文本
                                output = ""
                                for item in content:
                                    if isinstance(item, dict) and item.get("type") == "text":
                                        output += item.get("text", "")
                                    elif isinstance(item, dict) and item.get("type") == "output_text":
                                        output += item.get("text", "")
                                output = output.strip()
                            else:
                                output = str(content)

                            if not output:
                                continue

                            # 如果是 AI 消息，可能包含 <think> 思考标签，尝试提取其中的 JSON
                            if msg_type == "ai" and "<think>" in output:
                                # 移除思考标签，尝试提取 JSON
                                import re
                                # 方法1：提取 <think> 和 ]] 之间的高亮/思考内容
                                thinking_match = re.search(r'</think>\s*([\s\S]+?)\s*$', output)
                                if thinking_match:
                                    extracted = thinking_match.group(1).strip()
                                    # 尝试找 JSON 对象
                                    json_match = re.search(r'\{[\s\S]+\}', extracted)
                                    if json_match:
                                        output = json_match.group()
                                        logger.info(f"从 AI 思考内容中提取到 JSON（{len(output)} 字符）")
                                    else:
                                        # 如果没找到 JSON，使用清理后的思考内容
                                        output = extracted

                            if output:
                                logger.info(f"从 messages 中提取到输出（{len(output)} 字符）")
                                return output

                        # 如果没有找到有效输出
                        logger.warning("Run 完成但未找到有效输出")
                        return ""

                    return ""

                elif status in ["failed", "cancelled", "expired"]:
                    error_msg = run_status.get("error", "Run 执行失败")
                    logger.error(f"DeerFlow Run {status}: {error_msg}")
                    return None

                # 还在进行中，继续等待
                logger.debug(f"Run 状态: {status}，继续等待...")
                await asyncio.sleep(poll_interval)

            except Exception as e:
                logger.warning(f"轮询检查 Run 状态时出错: {e}")
                await asyncio.sleep(poll_interval)

    async def cleanup(self, thread_id: str, workspace_path: str | None = None) -> None:
        """
        清理 Thread 及其本地资源

        Args:
            thread_id: Thread ID
            workspace_path: 工作空间路径（可选，用于清理本地目录）
        """
        # 1. 调用 DeerFlow API 清理 Thread
        success = await self._cleanup_client.delete_thread(thread_id)
        if success:
            logger.info(f"DeerFlow Thread 清理成功: {thread_id}")
        else:
            logger.warning(f"DeerFlow Thread 清理失败: {thread_id}")

        # 2. 清理本地目录
        if workspace_path:
            thread_dir = Path(workspace_path).parent.parent  # workspace/user-data -> thread
            if thread_dir.exists():
                try:
                    import shutil
                    shutil.rmtree(thread_dir)
                    logger.info(f"本地目录清理成功: {thread_dir}")
                except Exception as e:
                    logger.warning(f"本地目录清理失败: {e}")
