"""Executor Service - AI 执行编排"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...domain.repository import IssueRepository

from ...domain.model import Issue, Stage, StageStatus
from ...domain.statemachine import StageStateMachine, LoggerHook
from ...infrastructure.agent import BaseAgent, MockAgent

logger = logging.getLogger(__name__)

# 系统指令目录
INSTRUCTIONS_DIR = Path.home() / ".swallowloop" / "instructions"


class ExecutorService:
    """AI 执行服务 - Issue 流水线阶段执行"""

    def __init__(self, repository: "IssueRepository", agent: BaseAgent | None = None, agent_type: str = "mock"):
        self._repo = repository
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._agent = agent or self._create_agent(agent_type)
        self._hooks = [LoggerHook()]

    def _create_agent(self, agent_type: str = "mock") -> BaseAgent:
        """根据配置创建 Agent"""
        if agent_type == "mock":
            logger.info("使用 MockAgent，延迟 5 秒")
            return MockAgent(delay_seconds=5.0)
        else:
            # 未来支持真实 Agent
            logger.warning(f"Agent 类型 '{agent_type}' 暂不支持，使用 MockAgent")
            return MockAgent(delay_seconds=5.0)

    def _get_machine(self, issue: Issue) -> StageStateMachine:
        """获取状态机实例"""
        return StageStateMachine(issue, self._repo, self._hooks)

    def get_workspace_dir(self, project: str, issue_id: str) -> Path:
        """获取工作空间目录"""
        return Path.home() / ".swallowloop" / project / str(issue_id) / "stages"

    def get_stage_dir(self, project: str, issue_id: str, stage: Stage) -> Path:
        """获取阶段目录"""
        return self.get_workspace_dir(project, issue_id) / stage.value

    def prepare_stage_context(self, project: str, issue_id: str, stage: Stage, document: str) -> Path:
        """准备阶段上下文并返回 context.md 路径"""
        stage_dir = self.get_stage_dir(project, issue_id, stage)
        stage_dir.mkdir(parents=True, exist_ok=True)

        # 读取指令文件
        instruction_file = INSTRUCTIONS_DIR / f"{stage.value}.md"
        instruction = ""
        if instruction_file.exists():
            instruction = instruction_file.read_text()

        # 生成 context.md
        context_path = stage_dir / "context.md"
        context_content = f"""# 阶段: {stage.value}

## 指令
{instruction}

## Issue 文档
{document}
"""
        context_path.write_text(context_content, encoding="utf-8")
        logger.debug(f"生成 context.md: {context_path}")

        return context_path

    async def execute_stage(self, issue: Issue, stage: Stage) -> dict:
        """异步执行阶段

        状态转换:
        - NEW → RUNNING (start)
        - REJECTED/ERROR → RUNNING (retry)
        - RUNNING → PENDING (execute)
        """
        project = "default"
        machine = self._get_machine(issue)

        # 根据当前状态决定转换方式
        current_status = issue.get_stage_state(stage).status
        if current_status == StageStatus.NEW:
            machine.start(stage)  # NEW → RUNNING
            logger.info(f"阶段 {stage.value} 从 NEW 转为 RUNNING")
        elif current_status in [StageStatus.REJECTED, StageStatus.ERROR]:
            machine.retry(stage)  # REJECTED/ERROR → RUNNING
            logger.info(f"阶段 {stage.value} 从 {current_status.value} 转为 RUNNING")

        # 准备上下文
        stage_state = issue.get_stage_state(stage)
        context_path = self.prepare_stage_context(project, str(issue.id), stage, stage_state.document)

        # 调用 Agent 执行
        context = {
            "issue_id": str(issue.id),
            "title": issue.title,
            "description": issue.description,
            "stage": stage.value,
            "document": stage_state.document,
            "context_path": str(context_path),
        }

        task_description = f"执行阶段 {stage.value}：{issue.title}"

        logger.info(f"开始执行 Agent 任务: {task_description}")
        result = await self._agent.execute(task_description, context)

        # 根据执行结果转换状态：RUNNING → PENDING 或 ERROR
        if result.success:
            # 将 Agent 输出写入 document
            stage_state.document = result.output or ""
            machine.execute(stage)  # RUNNING → PENDING
            logger.info(f"Agent 执行成功，阶段 {stage.value} 等待人工审批")
        else:
            machine.error(stage)  # RUNNING → ERROR
            logger.error(f"Agent 执行失败，阶段 {stage.value} 转为 ERROR: {result.error}")

        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
        }

    def execute_stage_async(self, issue: Issue, stage: Stage) -> None:
        """异步执行阶段（非阻塞）"""
        task_key = f"{issue.id}_{stage.value}"
        if task_key in self._running_tasks:
            logger.warning(f"任务已在执行中: {task_key}")
            return

        loop = asyncio.get_event_loop()
        task = loop.create_task(self.execute_stage(issue, stage))
        self._running_tasks[task_key] = task
        task.add_done_callback(lambda _: self._running_tasks.pop(task_key, None))
