"""Executor Service - AI 执行编排"""

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ...domain.repository import IssueRepository

from ...domain.model import Issue, Stage, Task, TaskId
from ...infrastructure.agent import ExecutionResult

logger = logging.getLogger(__name__)

# 系统指令目录
INSTRUCTIONS_DIR = Path.home() / ".swallowloop" / "instructions"


class AgentPort(Protocol):
    """Agent 端口协议"""

    def execute(self, task: Task, workspace_path: Path) -> ExecutionResult:
        """执行任务"""
        ...


class ExecutorService:
    """AI 执行服务 - Issue 流水线阶段执行"""

    def __init__(self, agent: AgentPort | None, repository: "IssueRepository"):
        self._agent = agent
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
        """异步执行阶段"""
        project = "default"  # TODO: 从配置获取

        # 准备上下文
        stage_state = issue.get_stage_state(stage)
        context_path = self.prepare_stage_context(project, str(issue.id), stage, stage_state.document)

        if self._agent is None:
            logger.warning(f"Agent 未配置，跳过执行阶段 {stage.value}")
            return {"success": False, "message": "Agent 未配置"}

        # 创建 Task（用于 Agent 执行）
        from ...domain.model import Task, TaskId
        task_id = TaskId(value=f"pipeline-{issue.id.value}-{stage.value}")
        task = Task(
            task_id=task_id,
            issue_number=int(issue.id.value.replace("issue-", ""), 16) % 100000,
            title=f"Issue Pipeline: {issue.title}",
            description=self._build_prompt(stage, context_path),
            branch_name=f"issue/{stage.value}",
        )

        # 在线程池中执行（避免阻塞事件循环）
        stage_dir = self.get_stage_dir(project, str(issue.id), stage)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._agent.execute(task, stage_dir)
        )

        # 保存产出
        if result.success:
            output_path = stage_dir / "output.md"
            output_path.write_text(result.output or "", encoding="utf-8")

            # 更新 document 字段并保存
            stage_state.document = result.output or ""
            self._repo.save(issue)

        return {
            "success": result.success,
            "output": result.output,
            "message": result.message,
        }

    def _build_prompt(self, stage: Stage, context_path: Path) -> str:
        """构建发送给 Agent 的提示"""
        context_content = ""
        if context_path.exists():
            context_content = context_path.read_text(encoding="utf-8")

        return f"""请执行 {stage.value} 阶段任务。

{context_content}

请根据上述指令和上下文完成阶段任务，并将产出写入 output.md 文件。"""

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
