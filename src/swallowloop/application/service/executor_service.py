"""Executor Service - AI 执行编排"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...domain.repository import IssueRepository

from ...domain.model import Issue, Stage, StageStatus, TodoStatus
from ...domain.pipeline import IssuePipeline, STAGE_INSTRUCTIONS
from ..dto import issue_to_dict, build_pipeline_info
from ...infrastructure.agent import BaseAgent, create_agent
from ...infrastructure.logger import sanitize_log_message
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# 系统指令目录
INSTRUCTIONS_DIR = Path.home() / ".swallowloop" / "instructions"


class ExecutorService:
    """AI 执行服务 - Issue 流水线阶段执行"""

    def __init__(self, repository: "IssueRepository", agent: BaseAgent | None = None, agent_type: str = "deerflow", ws_manager=None):
        self._repo = repository
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._agent = agent or create_agent(agent_type)
        self._hooks = []
        self._ws_manager = ws_manager

    async def _broadcast(self, msg_type: str, data: dict):
        """广播消息到 WebSocket 客户端"""
        if self._ws_manager:
            try:
                await self._ws_manager.broadcast_issue({"type": msg_type, **data})
            except Exception as e:
                logger.warning(f"WebSocket 广播失败: {e}")

    def _get_stage_instruction(self, stage: Stage) -> str:
        """获取阶段指令（优先从内置字典读取，否则从文件读取）"""
        # 1. 优先从内置字典读取
        if stage.value in STAGE_INSTRUCTIONS:
            return STAGE_INSTRUCTIONS[stage.value]
        # 2. 回退到文件读取
        instruction_file = INSTRUCTIONS_DIR / f"{stage.value}.md"
        if instruction_file.exists():
            return instruction_file.read_text(encoding="utf-8")
        return ""

    def get_issue(self, issue_id) -> "Issue | None":
        """获取 Issue（通过 repository）"""
        return self._repo.get(issue_id)

    async def execute_stage(self, issue: Issue, stage: Stage) -> dict:
        """异步执行阶段（统一使用 Pipeline）

        状态转换:
        - NEW → RUNNING
        - REJECTED/ERROR → RUNNING
        - RUNNING → PENDING 或 ERROR
        """
        stage_state = issue.get_stage_state(stage)
        current_status = stage_state.status

        # 检查状态，只有 NEW/REJECTED/ERROR 才能触发
        if current_status not in [StageStatus.NEW, StageStatus.REJECTED, StageStatus.ERROR]:
            logger.warning(f"阶段 {stage.value} 状态为 {current_status.value}，不能触发")
            return {"success": False, "error": f"阶段状态为 {current_status.value}，不能触发"}

        # 1. 状态转换 NEW/REJECTED/ERROR → RUNNING
        if current_status == StageStatus.NEW:
            stage_state.status = StageStatus.RUNNING
            stage_state.started_at = datetime.now()
            logger.info(f"阶段 {stage.value} 从 NEW 转为 RUNNING")
        elif current_status in [StageStatus.REJECTED, StageStatus.ERROR]:
            stage_state.status = StageStatus.RUNNING
            stage_state.started_at = datetime.now()
            logger.info(f"阶段 {stage.value} 从 {current_status.value} 转为 RUNNING")

        # 2. 更新任务状态为执行中
        if stage_state.todo_list:
            for todo in stage_state.todo_list:
                todo.status = TodoStatus.IN_PROGRESS
        self._repo.save(issue)

        # 3. 广播状态更新
        await self._broadcast("issue_updated", {"issue": issue_to_dict(issue)})

        # 4. 设置 agent 以便 Pipeline 调用
        if self._agent:
            issue.pipeline.set_agent(self._agent)

        # 5. 通过 Pipeline 执行阶段
        if stage == Stage.ENVIRONMENT:
            result = issue.pipeline.execute_environment()
        else:
            result = await issue.pipeline.execute_stage(stage.value)

        # 6. Pipeline 执行完后，同步 workspace 信息到 issue（仅 ENVIRONMENT 阶段）
        if stage == Stage.ENVIRONMENT:
            pipeline_context = issue.pipeline.get_context()
            logger.info(f"Pipeline context after execute_environment: workspace_path={pipeline_context.workspace_path}, thread_id={pipeline_context.thread_id}")
            if pipeline_context.workspace_path:
                issue.thread_path = pipeline_context.workspace_path
            if pipeline_context.thread_id:
                issue.thread_id = pipeline_context.thread_id
            if pipeline_context.workspace_path:
                from ...domain.model.workspace import Workspace
                issue.workspace = Workspace(
                    id=pipeline_context.thread_id or issue.thread_id or "",
                    ready=True,
                    workspace_path=pipeline_context.workspace_path,
                    repo_url=pipeline_context.repo_url or issue.repo_url or "",
                    branch=pipeline_context.branch or str(issue.id),
                )

        # 6.5. 同步 SDD 阶段结果到 stage_state.stage_content
        sdd_result_keys = ["specify_result", "clarify_result", "plan_result",
                          "checklist_result", "tasks_result", "analyze_result",
                          "implement_result"]
        for key in sdd_result_keys:
            if result.get("success") and result.get(key):
                stage_content = result.get(key, "")
                stage_state.stage_content = stage_content
                logger.info(f"{stage.value} 结果已存储: {len(stage_content)} 字符")
                break

        # 7. 更新任务状态
        if stage_state.todo_list:
            for i, todo in enumerate(stage_state.todo_list):
                if result.get("success"):
                    todo.status = TodoStatus.COMPLETED
                else:
                    todo.status = TodoStatus.FAILED

        # 8. 更新阶段状态
        if result.get("success"):
            stage_state.status = StageStatus.PENDING
            stage_state.document = result.get("output", result.get("message", ""))
        else:
            stage_state.status = StageStatus.ERROR

        self._repo.save(issue)
        await self._broadcast("issue_updated", {"issue": issue_to_dict(issue)})

        return result

