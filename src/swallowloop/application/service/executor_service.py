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
from ...infrastructure.agent import BaseAgent, MockAgent, DeerFlowAgent

logger = logging.getLogger(__name__)

# 系统指令目录
INSTRUCTIONS_DIR = Path.home() / ".swallowloop" / "instructions"


class ExecutorService:
    """AI 执行服务 - Issue 流水线阶段执行"""

    def __init__(self, repository: "IssueRepository", agent: BaseAgent | None = None, agent_type: str = "mock", ws_manager=None):
        self._repo = repository
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._agent = agent or self._create_agent(agent_type)
        self._hooks = [LoggerHook()]
        self._ws_manager = ws_manager

    async def _broadcast(self, msg_type: str, data: dict):
        """广播消息到 WebSocket 客户端"""
        if self._ws_manager:
            try:
                await self._ws_manager.broadcast_issue({"type": msg_type, **data})
            except Exception as e:
                logger.warning(f"WebSocket 广播失败: {e}")

    def _create_agent(self, agent_type: str = "mock") -> BaseAgent:
        """根据配置创建 Agent"""
        if agent_type == "mock":
            logger.info("使用 MockAgent，延迟 5 秒")
            return MockAgent(delay_seconds=5.0)
        elif agent_type == "deerflow":
            logger.info("使用 DeerFlowAgent")
            return DeerFlowAgent()
        else:
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

    async def prepare_workspace(self, issue: Issue, stage: Stage) -> bool:
        """准备工作空间（在 submit 之前调用）

        1. 调用 agent.prepare() 创建 workspace
        2. 创建 stages/{stage}/ 目录
        3. 保存 issue 到仓库（让 worker 能看到 workspace）

        Returns:
            True if success, False otherwise
        """
        project = "default"
        stage_state = issue.get_stage_state(stage)

        # 1. 调用 agent.prepare() 准备工作空间
        if self._agent:
            context = {
                "repo_url": issue.repo_url or (self._settings.github_repo if self._settings else ""),
                "branch": str(issue.id),
                "stage": stage.value,
            }
            try:
                workspace_info = await self._agent.prepare(str(issue.id), context)
                issue.workspace = workspace_info
            except Exception as e:
                logger.error(f"agent.prepare() 失败: {e}")
                return False

        # 2. 创建 stages/{stage}/ 目录
        try:
            context_path = self.prepare_stage_context(project, str(issue.id), stage, stage_state.document)
            if not context_path.parent.exists():
                logger.error(f"工作空间目录创建失败: {context_path.parent}")
                return False
        except Exception as e:
            logger.error(f"prepare_stage_context() 失败: {e}")
            return False

        # 3. 保存 issue（workspace 已设置）
        self._repo.save(issue)

        logger.info(f"工作空间准备完成: {issue.id}/{stage.value}")
        return True

    async def execute_stage(self, issue: Issue, stage: Stage) -> dict:
        """异步执行阶段（假设 workspace 已通过 prepare_workspace 创建）

        状态转换:
        - NEW → RUNNING (start)
        - REJECTED/ERROR → RUNNING (retry)
        - RUNNING → PENDING (execute)
        """
        project = "default"
        machine = self._get_machine(issue)
        stage_state = issue.get_stage_state(stage)
        current_status = stage_state.status

        # 1. 状态转换 NEW/REJECTED/ERROR → RUNNING
        if current_status == StageStatus.NEW:
            machine.start(stage)  # NEW → RUNNING
            logger.info(f"阶段 {stage.value} 从 NEW 转为 RUNNING")
        elif current_status in [StageStatus.REJECTED, StageStatus.ERROR]:
            machine.retry(stage)  # REJECTED/ERROR → RUNNING
            logger.info(f"阶段 {stage.value} 从 {current_status.value} 转为 RUNNING")

        # 2. 广播状态更新
        await self._broadcast("issue_updated", {"issue": self._issue_to_dict(issue)})

        # 3. 调用 Agent 执行
        # context_path 从已创建的 workspace 获取
        workspace_path = Path(issue.workspace.workspace_path) if issue.workspace else None
        context_path = workspace_path / stage.value / "context.md" if workspace_path else None

        context = {
            "issue_id": str(issue.id),
            "title": issue.title,
            "description": issue.description,
            "stage": stage.value,
            "document": stage_state.document,
            "context_path": str(context_path) if context_path else None,
            "thread_id": issue.workspace.id if issue.workspace else None,
            "workspace_path": issue.workspace.workspace_path if issue.workspace else None,
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

        # 广播状态更新
        await self._broadcast("issue_updated", {"issue": self._issue_to_dict(issue)})

        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
        }

    def _issue_to_dict(self, issue: Issue) -> dict:
        """将 Issue 序列化为字典"""
        return {
            "id": str(issue.id),
            "title": issue.title,
            "description": issue.description,
            "status": issue.status.value,
            "currentStage": issue.current_stage.value,
            "createdAt": issue.created_at.isoformat(),
            "archivedAt": issue.archived_at.isoformat() if issue.archived_at else None,
            "discardedAt": issue.discarded_at.isoformat() if issue.discarded_at else None,
            "stages": {
                stage.value: {
                    "stage": stage.value,
                    "status": state.status.value,
                    "document": state.document,
                    "comments": [
                        {
                            "id": c.id,
                            "stage": c.stage.value,
                            "action": c.action,
                            "content": c.content,
                            "createdAt": c.created_at.isoformat(),
                        }
                        for c in state.comments
                    ],
                    "startedAt": state.started_at.isoformat() if state.started_at else None,
                    "completedAt": state.completed_at.isoformat() if state.completed_at else None,
                }
                for stage, state in issue.stages.items()
            },
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
