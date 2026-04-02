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
from ...domain.pipeline import IssuePipeline, PipelineContext
from ...infrastructure.agent import BaseAgent, create_agent
from .executor import IExecutor
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# 系统指令目录
INSTRUCTIONS_DIR = Path.home() / ".swallowloop" / "instructions"


class ExecutorService(IExecutor):
    """AI 执行服务 - Issue 流水线阶段执行"""

    def __init__(self, repository: "IssueRepository", agent: BaseAgent | None = None, agent_type: str = "mock", ws_manager=None):
        self._repo = repository
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._agent = agent or self._create_agent(agent_type)
        self._hooks = []
        self._ws_manager = ws_manager

    async def _broadcast(self, msg_type: str, data: dict):
        """广播消息到 WebSocket 客户端"""
        if self._ws_manager:
            try:
                await self._ws_manager.broadcast_issue({"type": msg_type, **data})
            except Exception as e:
                logger.warning(f"WebSocket 广播失败: {e}")

    def _create_agent(self, agent_type: str = "mock") -> BaseAgent:
        """根据配置创建 Agent（工厂函数）"""
        return create_agent(agent_type)

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

    def _generate_stage_file(self, issue: Issue, stage: Stage, stage_state, prev_result: dict | None = None) -> tuple[str, str]:
        """
        生成 Stage 文件

        Returns:
            (stage_file_path, result_file_path)
        """
        workspace_path = Path(issue.workspace.workspace_path) if issue.workspace else None
        if not workspace_path:
            raise ValueError("Issue workspace not initialized")

        # Stage 文件路径: {stage_id}-{name}.md
        stage_file = workspace_path / f"{stage.value}.md"
        result_file = workspace_path / f"{stage.value}-result.json"

        # 读取指令文件
        instruction_file = INSTRUCTIONS_DIR / f"{stage.value}.md"
        instruction = ""
        if instruction_file.exists():
            instruction = instruction_file.read_text()

        # 构建上下文
        context_content = f"""# Stage {stage.value}

## 任务描述
{stage_state.document or instruction or "无"}

## 上下文
- Issue: {issue.title}
- Issue ID: {issue.id}
- 仓库: {issue.repo_url or "N/A"}
"""

        # 如果有上一个 Stage 的结果，添加为输入
        if prev_result:
            context_content += f"""
## 上一个 Stage 结果
```json
{json.dumps(prev_result, ensure_ascii=False, indent=2)}
```
"""

        context_content += f"""
## 期望输出
完成 {stage.value} 任务后，将结果写入 {result_file.name}
结果使用 JSON 格式：
{{
  "status": "success" | "failed",
  "output": "执行摘要",
  "files": ["生成的文件列表"],
  "error": "错误信息（如果有）"
}}
"""

        stage_file.write_text(context_content, encoding="utf-8")
        logger.debug(f"生成 stage 文件: {stage_file}")

        return str(stage_file), str(result_file)

    async def prepare_workspace(self, issue: Issue, stage: Stage) -> bool:
        """准备工作空间（在 submit 之前调用）

        1. 调用 agent.prepare() 创建 Thread
        2. 保存 thread_id 和 thread_path 到 issue
        3. 生成 stage 文件
        4. 保存 issue 到仓库

        Returns:
            True if success, False otherwise
        """
        stage_state = issue.get_stage_state(stage)

        # 1. 如果已有 thread_id，复用；否则创建新的
        if issue.thread_id:
            logger.info(f"Issue {issue.id} 已有 thread_id={issue.thread_id}，复用")
            workspace_path = Path(issue.thread_path) if issue.thread_path else None
            if not workspace_path:
                workspace_path = (
                    Path.home() / ".deer-flow" / "threads" / issue.thread_id / "user-data" / "workspace"
                ).resolve()
                issue.thread_path = str(workspace_path)
        else:
            # 调用 agent.prepare() 创建 Thread
            if self._agent:
                context = {
                    "repo_url": issue.repo_url or "",
                    "branch": str(issue.id),
                    "stage": stage.value,
                }
                try:
                    workspace_info = self._agent.prepare(str(issue.id), context)
                    issue.workspace = workspace_info
                    issue.thread_id = workspace_info.id
                    issue.thread_path = workspace_info.workspace_path
                    logger.info(f"DeerFlow Thread 创建成功: thread_id={issue.thread_id}")
                except Exception as e:
                    logger.error(f"agent.prepare() 失败: {e}")
                    return False
            else:
                logger.error("Agent 未配置")
                return False

        # 2. 生成 stage 文件
        try:
            workspace_path = Path(issue.thread_path)
            workspace_path.mkdir(parents=True, exist_ok=True)
            stage_file, result_file = self._generate_stage_file(issue, stage, stage_state)
            logger.info(f"Stage 文件已生成: {stage_file}")
        except Exception as e:
            logger.error(f"生成 stage 文件失败: {e}")
            return False

        # 3. 保存 issue
        self._repo.save(issue)

        logger.info(f"工作空间准备完成: {issue.id}/{stage.value}, thread_id={issue.thread_id}")
        return True

    async def execute_stage(self, issue: Issue, stage: Stage) -> dict:
        """异步执行阶段（假设 workspace 已通过 prepare_workspace 创建）

        状态转换:
        - NEW → RUNNING
        - REJECTED/ERROR → RUNNING
        - RUNNING → PENDING 或 ERROR
        """
        # ENVIRONMENT 阶段使用 Pipeline 执行
        if stage == Stage.ENVIRONMENT:
            return await self._execute_environment_stage(issue, stage)

        project = "default"
        stage_state = issue.get_stage_state(stage)
        current_status = stage_state.status

        # 1. 状态转换 NEW/REJECTED/ERROR → RUNNING
        if current_status == StageStatus.NEW:
            stage_state.status = StageStatus.RUNNING
            stage_state.started_at = datetime.now()
            logger.info(f"阶段 {stage.value} 从 NEW 转为 RUNNING")
        elif current_status in [StageStatus.REJECTED, StageStatus.ERROR]:
            stage_state.status = StageStatus.RUNNING
            stage_state.started_at = datetime.now()
            logger.info(f"阶段 {stage.value} 从 {current_status.value} 转为 RUNNING")

        # 2. 广播状态更新
        await self._broadcast("issue_updated", {"issue": self._issue_to_dict(issue)})

        # 3. 构建文件路径
        workspace_path = Path(issue.thread_path) if issue.thread_path else None
        if not workspace_path:
            logger.error("Issue 没有 thread_path")
            stage_state.status = StageStatus.ERROR
            return {"success": False, "output": "", "error": "thread_path not found"}

        stage_file = workspace_path / f"{stage.value}.md"
        result_file = workspace_path / f"{stage.value}-result.json"

        # 4. 构建任务指令
        task_message = f"""请读取并执行任务文件 {stage_file}，完成后将结果写入 {result_file}。"""

        context = {
            "thread_id": issue.thread_id,
            "stage_file": str(stage_file),
            "result_file": str(result_file),
        }

        logger.info(f"开始执行 DeerFlow 任务: thread_id={issue.thread_id}, stage={stage.value}")
        logger.debug(f"Task message: {task_message}")

        # 5. 调用 Agent 执行
        result = await self._agent.execute(task_message, context)

        # 6. 根据执行结果转换状态：RUNNING → PENDING 或 ERROR
        if result.success:
            # 读取 result.json 获取结构化输出
            try:
                if result_file.exists():
                    with open(result_file, "r", encoding="utf-8") as f:
                        result_data = json.load(f)
                        stage_state.document = result_data.get("output", result.output or "")
                    # 删除 result.json 表示已消费
                    result_file.unlink(missing_ok=True)
                else:
                    stage_state.document = result.output or ""
            except Exception as e:
                logger.warning(f"读取 result.json 失败: {e}")
                stage_state.document = result.output or ""

            stage_state.status = StageStatus.PENDING
            logger.info(f"DeerFlow 执行成功，阶段 {stage.value} 等待人工审批")
        else:
            stage_state.status = StageStatus.ERROR
            logger.error(f"DeerFlow 执行失败，阶段 {stage.value} 转为 ERROR: {result.error}")

        # 广播状态更新
        await self._broadcast("issue_updated", {"issue": self._issue_to_dict(issue)})

        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
        }

    async def _execute_environment_stage(self, issue: Issue, stage: Stage) -> dict:
        """执行环境准备阶段 - 使用 Pipeline"""
        stage_state = issue.get_stage_state(stage)
        current_status = stage_state.status

        # 状态转换 NEW/REJECTED/ERROR → RUNNING
        if current_status == StageStatus.NEW:
            stage_state.status = StageStatus.RUNNING
            stage_state.started_at = datetime.now()
        elif current_status in [StageStatus.REJECTED, StageStatus.ERROR]:
            stage_state.status = StageStatus.RUNNING
            stage_state.started_at = datetime.now()

        await self._broadcast("issue_updated", {"issue": self._issue_to_dict(issue)})

        # 从 repo_url 提取仓库名
        repo_name = "repo"
        if issue.repo_url:
            parsed = urlparse(issue.repo_url)
            path_parts = parsed.path.strip("/").split("/")
            if len(path_parts) >= 2:
                repo_name = path_parts[-1].replace(".git", "")

        # 构建 context
        context = PipelineContext(
            issue_id=str(issue.id),
            workspace_path=issue.thread_path or "",
            repo_url=issue.repo_url or "",
            repo_name=repo_name,
            branch=str(issue.id),
            thread_id=issue.thread_id or "",
        ).to_dict()

        # 获取 pipeline stage
        pipeline = IssuePipeline()
        stage_obj = pipeline.stages[0]  # environment 是第一个 stage

        # 按顺序执行每个任务，实时更新状态
        all_success = True
        for i, task in enumerate(stage_obj.tasks):
            # 更新任务状态为执行中
            if stage_state.todo_list and i < len(stage_state.todo_list):
                stage_state.todo_list[i].status = TodoStatus.IN_PROGRESS
            self._repo.save(issue)
            await self._broadcast("issue_updated", {"issue": self._issue_to_dict(issue)})

            # 执行任务
            context, task_result = task.execute(context)

            # 更新任务状态为完成/失败
            if stage_state.todo_list and i < len(stage_state.todo_list):
                if task_result.success:
                    stage_state.todo_list[i].status = TodoStatus.COMPLETED
                else:
                    stage_state.todo_list[i].status = TodoStatus.FAILED
                    all_success = False

            # 保存并广播
            self._repo.save(issue)
            await self._broadcast("issue_updated", {"issue": self._issue_to_dict(issue)})

            # 如果任务失败，停止执行
            if not task_result.success:
                break

        # 更新阶段状态
        if all_success:
            stage_state.status = StageStatus.PENDING
        else:
            stage_state.status = StageStatus.ERROR

        self._repo.save(issue)
        await self._broadcast("issue_updated", {"issue": self._issue_to_dict(issue)})

        return {"success": all_success, "message": f"环境准备阶段{'完成' if all_success else '失败'}"}

    def _issue_to_dict(self, issue: Issue) -> dict:
        """将 Issue 序列化为字典"""
        return {
            "id": str(issue.id),
            "title": issue.title,
            "description": issue.description,
            "status": issue.status.value,
            "currentStage": issue.current_stage.value,
            "runningStatus": issue.running_status.value,
            "createdAt": issue.created_at.isoformat(),
            "archivedAt": issue.archived_at.isoformat() if issue.archived_at else None,
            "discardedAt": issue.discarded_at.isoformat() if issue.discarded_at else None,
            "workspace": {
                "id": issue.workspace.id if issue.workspace else None,
                "ready": issue.workspace.ready if issue.workspace else False,
                "workspace_path": issue.workspace.workspace_path if issue.workspace else "",
                "repo_url": issue.workspace.repo_url if issue.workspace else "",
                "branch": issue.workspace.branch if issue.workspace else "",
                "thread_id": issue.thread_id or "",
            } if issue.workspace else None,
            "repo_url": issue.repo_url,
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
                    "todoList": [
                        {"id": t.id, "content": t.content, "status": t.status.value}
                        for t in state.todo_list
                    ] if state.todo_list else [],
                }
                for stage, state in issue.stages.items()
            },
            "pipeline": self._build_pipeline_info(issue),
        }

    def _build_pipeline_info(self, issue: Issue) -> dict:
        """构建 Pipeline 展示信息"""
        from ...domain.model import Stage as DomainStage

        stages_info = []
        for stage in DomainStage:
            state = issue.stages.get(stage)
            if state:
                tasks = []
                if state.todo_list:
                    for todo in state.todo_list:
                        tasks.append({
                            "name": todo.content,
                            "status": todo.status.value,
                        })
                stages_info.append({
                    "name": stage.value,
                    "label": self._get_stage_label(stage),
                    "status": state.status.value,
                    "startedAt": state.started_at.isoformat() if state.started_at else None,
                    "completedAt": state.completed_at.isoformat() if state.completed_at else None,
                    "tasks": tasks,
                })

        current_index = 0
        for i, stage in enumerate(DomainStage):
            if stage == issue.current_stage:
                current_index = i
                break

        return {
            "name": f"Issue-{issue.id}",
            "stages": stages_info,
            "currentStageIndex": current_index,
            "isDone": issue.status.value in ["archived", "done"],
        }

    def _get_stage_label(self, stage) -> str:
        """获取阶段中文标签"""
        labels = {
            "environment": "环境准备",
            "brainstorm": "头脑风暴",
            "planFormed": "方案制定",
            "detailedDesign": "详细设计",
            "taskSplit": "任务拆分",
            "execution": "执行",
            "updateDocs": "更新文档",
            "submit": "提交",
        }
        return labels.get(stage.value, stage.value)

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
