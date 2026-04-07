"""Issue 应用服务"""

import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .executor import IExecutor
    from ...infrastructure.agent import BaseAgent
    from ...infrastructure.config import Config

from ...domain.model import Issue, IssueId, Stage, IssueStatus, IssueRunningStatus, Workspace, StageStatus, TodoStatus
from ...domain.repository import IssueRepository
from ...domain.pipeline import IssuePipeline

logger = logging.getLogger(__name__)


class IssueService:
    """Issue 应用服务"""

    def __init__(self, repository: IssueRepository, executor: "IExecutor", agent: "BaseAgent | None" = None, config: "Config | None" = None, ws_manager=None):
        self._repo = repository
        self._executor = executor
        self._agent = agent
        self._config = config
        self._hooks = []
        self._ws_manager = ws_manager

    async def _broadcast(self, msg_type: str, data: dict):
        """广播消息到 WebSocket 客户端"""
        if self._ws_manager:
            try:
                await self._ws_manager.broadcast_issue({"type": msg_type, **data})
            except Exception as e:
                logger.warning(f"WebSocket 广播失败: {e}")

    def _advance_to_next_stage(self, issue: Issue, current_stage: Stage) -> bool:
        """推进到下一阶段（APPROVED 后调用）"""
        stages = list(Stage)
        current_idx = stages.index(current_stage)

        # 检查是否是最后一个阶段
        if current_idx >= len(stages) - 1:
            # 最后一个阶段已通过，标记为完成
            issue.mark_done()
            return True

        next_stage = stages[current_idx + 1]
        issue.create_stage(next_stage)
        issue.current_stage = next_stage
        return True

    def list_issues(self) -> list[Issue]:
        """获取所有 Issue"""
        return self._repo.list_all()

    def get_issue(self, issue_id: str) -> Issue | None:
        """获取单个 Issue"""
        return self._repo.get(IssueId(issue_id))

    async def create_issue(self, title: str, description: str) -> Issue:
        """创建新 Issue（NEW 状态，由 StageLoop 自动触发 AI）"""
        issue_id = IssueId(f"issue-{uuid.uuid4().hex[:8]}")

        # 从配置获取仓库信息
        repo_url = ""
        repo_branch = "main"
        if self._config:
            repo_config = self._config.get_repository()
            repo_url = repo_config.get("url", "")
            repo_branch = repo_config.get("branch", "main")

        # 创建 Issue（Pipeline 在 Issue.__post_init__ 中自动创建）
        issue = Issue(
            id=issue_id,
            title=title,
            description=description,
            status=IssueStatus.ACTIVE,
            current_stage=Stage.ENVIRONMENT,
            created_at=datetime.now(),
            repo_url=repo_url,
        )
        # 更新 pipeline.context 的属性
        issue.pipeline.set_context_value("repo_url", repo_url)
        issue.pipeline.set_context_value("branch", repo_branch)
        issue.pipeline.get_context().extra["issue_title"] = title
        issue.pipeline.get_context().extra["issue_description"] = description

        # 创建环境准备阶段（状态为 NEW，由 StageLoop 自动触发 AI）
        issue.create_stage(Stage.ENVIRONMENT)
        self._repo.save(issue)
        logger.info(f"创建 Issue: {issue_id} - {title}，current_stage={issue.current_stage.value}, "
                    f"BRAINSTORM.status={issue.get_stage_state(Stage.BRAINSTORM).status.value}")

        # 广播创建事件
        await self._broadcast("issue_created", {"issue": self._issue_to_dict(issue)})
        return issue

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
        stages_info = []
        for stage in Stage:
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
        for i, stage in enumerate(Stage):
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

    async def approve_stage(self, issue_id: str, stage: Stage, comment: str = "") -> Issue | None:
        """审批通过阶段"""
        issue = self._repo.get(IssueId(issue_id))
        if not issue:
            return None

        # 直接更新阶段状态
        stage_state = issue.get_stage_state(stage)
        stage_state.status = StageStatus.APPROVED
        stage_state.completed_at = datetime.now()
        self._advance_to_next_stage(issue, stage)  # → 下一阶段 NEW

        logger.info(f"Issue {issue_id} 阶段 {stage.value} 审批通过")
        await self._broadcast("issue_updated", {"issue": self._issue_to_dict(issue)})
        return issue

    async def reject_stage(self, issue_id: str, stage: Stage, reason: str) -> Issue | None:
        """打回阶段"""
        issue = self._repo.get(IssueId(issue_id))
        if not issue:
            return None

        # 直接更新阶段状态
        stage_state = issue.get_stage_state(stage)
        stage_state.status = StageStatus.REJECTED

        logger.info(f"Issue {issue_id} 阶段 {stage.value} 已打回: {reason}")
        await self._broadcast("issue_updated", {"issue": self._issue_to_dict(issue)})
        return issue

    async def trigger_ai(self, issue_id: str, stage: Stage) -> dict:
        """手动触发 AI 执行

        流程：
        1. executor.prepare_workspace() 创建 workspace 和 stages/{stage}/
        2. executor.execute_stage() 处理状态转换和执行
        """
        issue = self._repo.get(IssueId(issue_id))
        if not issue:
            return {"status": "error", "message": "Issue not found"}

        # 标记为进行中
        issue.mark_in_progress()
        self._repo.save(issue)

        # 必须是当前阶段才能触发
        if issue.current_stage != stage:
            return {"status": "error", "message": f"只能触发当前阶段，当前阶段是 {issue.current_stage.value}"}

        stage_state = issue.get_stage_state(stage)
        if stage_state.status not in [StageStatus.NEW, StageStatus.REJECTED, StageStatus.ERROR]:
            return {"status": "error", "message": f"当前状态 {stage_state.status.value} 不能触发 AI"}

        # 1. 准备 workspace
        if not await self._executor.prepare_workspace(issue, stage):
            return {"status": "error", "message": "workspace 准备失败"}

        # 2. 同步 workspace 信息到 pipeline.context
        if issue.thread_path:
            issue.pipeline.set_context_value("workspace_path", issue.thread_path)
            issue.pipeline.set_context_value("thread_id", issue.thread_id)

        # 3. 环境准备阶段使用 Pipeline 执行
        if stage == Stage.ENVIRONMENT:
            return await self._execute_environment_stage(issue, stage)

        # 3. 其他阶段使用 executor 处理
        result = await self._executor.execute_stage(issue, stage)
        return result

    async def _execute_environment_stage(self, issue: Issue, stage: Stage) -> dict:
        """执行环境准备阶段 - 使用 Pipeline"""
        stage_state = issue.get_stage_state(stage)

        # 状态转换 NEW/REJECTED/ERROR → RUNNING
        if stage_state.status == StageStatus.NEW:
            stage_state.status = StageStatus.RUNNING
            stage_state.started_at = datetime.now()
        elif stage_state.status in [StageStatus.REJECTED, StageStatus.ERROR]:
            stage_state.status = StageStatus.RUNNING
            stage_state.started_at = datetime.now()

        # 更新任务状态为执行中
        if stage_state.todo_list:
            for todo in stage_state.todo_list:
                todo.status = TodoStatus.IN_PROGRESS
        self._repo.save(issue)
        await self._broadcast("issue_updated", {"issue": self._issue_to_dict(issue)})

        # 调用 Pipeline 执行环境准备
        # 设置 agent 以便 Pipeline 注入 agent 到 tasks
        agent = getattr(self._executor, '_agent', None)
        if agent is not None:
            issue.pipeline.set_agent(agent)
        result = issue.pipeline.execute_environment()

        # 更新任务状态
        if stage_state.todo_list:
            for i, todo in enumerate(stage_state.todo_list):
                if result.get("success"):
                    todo.status = TodoStatus.COMPLETED
                else:
                    todo.status = TodoStatus.FAILED

        # 更新阶段状态
        if result.get("success"):
            stage_state.status = StageStatus.PENDING
        else:
            stage_state.status = StageStatus.ERROR

        self._repo.save(issue)
        await self._broadcast("issue_updated", {"issue": self._issue_to_dict(issue)})

        return result

    def update_issue(self, issue_id: str, **kwargs) -> Issue | None:
        """更新 Issue"""
        issue = self._repo.get(IssueId(issue_id))
        if not issue:
            return None

        if "title" in kwargs:
            issue.title = kwargs["title"]
        if "description" in kwargs:
            issue.description = kwargs["description"]
        if "status" in kwargs:
            if kwargs["status"] == "archived":
                issue.status = IssueStatus.ARCHIVED
                issue.archived_at = datetime.now()
            elif kwargs["status"] == "discarded":
                issue.status = IssueStatus.DISCARDED
                issue.discarded_at = datetime.now()
        if "runningStatus" in kwargs:
            issue.running_status = IssueRunningStatus(kwargs["runningStatus"])

        self._repo.save(issue)
        return issue

    def archive_issue(self, issue_id: str) -> Issue | None:
        """归档 Issue"""
        return self.update_issue(issue_id, status="archived")

    def discard_issue(self, issue_id: str) -> Issue | None:
        """废弃 Issue"""
        return self.update_issue(issue_id, status="discarded")

    async def delete_issue(self, issue_id: str) -> bool:
        """删除 Issue（硬删除）"""
        issue_id_obj = IssueId(issue_id)
        # 硬删除：直接从仓库移除
        success = self._repo.delete(issue_id_obj)
        if success:
            logger.info(f"删除 Issue: {issue_id}")
            # 广播删除事件
            await self._broadcast("issue_deleted", {"issue_id": issue_id})
        return success
