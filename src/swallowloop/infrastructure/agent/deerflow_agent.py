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

logger = logging.getLogger(__name__)

# 轮询配置
POLL_INTERVAL_SECONDS = 20  # 轮询间隔
MAX_EXECUTE_TIMEOUT_SECONDS = 1800  # 最大执行时间 30 分钟


class DeerFlowAgent(BaseAgent):
    """DeerFlow Agent - 通过 HTTP API 与 DeerFlow 通信"""

    def __init__(self, base_url: str = "http://localhost:2026"):
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

    async def initialize(self) -> None:
        """检查 DeerFlow 连接"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
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
            async with httpx.AsyncClient(timeout=5.0) as client:
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
            async with httpx.AsyncClient(timeout=5.0) as client:
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

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
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
