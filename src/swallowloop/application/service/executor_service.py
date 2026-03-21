"""Executor Service - AI 执行编排

暂不支持 AI 执行，仅提供基础阶段管理功能。
"""

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...domain.repository import IssueRepository

from ...domain.model import Issue, Stage

logger = logging.getLogger(__name__)

# 系统指令目录
INSTRUCTIONS_DIR = Path.home() / ".swallowloop" / "instructions"


class ExecutorService:
    """AI 执行服务 - Issue 流水线阶段执行（暂不支持 AI）"""

    def __init__(self, repository: "IssueRepository"):
        self._repo = repository
        self._running_tasks: dict[str, asyncio.Task] = {}

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
        """异步执行阶段（暂不支持 AI，仅更新文档）"""
        project = "default"

        # 准备上下文
        stage_state = issue.get_stage_state(stage)
        context_path = self.prepare_stage_context(project, str(issue.id), stage, stage_state.document)

        logger.warning(f"AI 执行暂不支持，请手动完成阶段 {stage.value}")

        return {
            "success": True,
            "output": "AI 执行暂不支持，阶段已准备",
            "message": "阶段上下文已准备好，但 AI 执行功能尚未实现",
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
