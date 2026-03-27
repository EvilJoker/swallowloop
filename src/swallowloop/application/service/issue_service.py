"""Issue 应用服务"""

import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .executor import IExecutor
    from ...infrastructure.agent import BaseAgent
    from ...infrastructure.config import Settings

from ...domain.model import Issue, IssueId, Stage, IssueStatus, Workspace
from ...domain.repository import IssueRepository
from ...domain.statemachine import StageStateMachine, LoggerHook

logger = logging.getLogger(__name__)


class IssueService:
    """Issue 应用服务"""

    def __init__(self, repository: IssueRepository, executor: "IExecutor", agent: "BaseAgent | None" = None, settings: "Settings | None" = None, ws_manager=None):
        self._repo = repository
        self._executor = executor
        self._agent = agent
        self._settings = settings
        self._hooks = [LoggerHook()]
        self._ws_manager = ws_manager

    async def _broadcast(self, msg_type: str, data: dict):
        """广播消息到 WebSocket 客户端"""
        if self._ws_manager:
            try:
                await self._ws_manager.broadcast_issue({"type": msg_type, **data})
            except Exception as e:
                logger.warning(f"WebSocket 广播失败: {e}")

    def _get_machine(self, issue: Issue) -> StageStateMachine:
        return StageStateMachine(issue, self._repo, self._hooks)

    def list_issues(self) -> list[Issue]:
        """获取所有 Issue"""
        return self._repo.list_all()

    def get_issue(self, issue_id: str) -> Issue | None:
        """获取单个 Issue"""
        return self._repo.get(IssueId(issue_id))

    async def create_issue(self, title: str, description: str) -> Issue:
        """创建新 Issue（NEW 状态，由 StageLoop 自动触发 AI）"""
        issue_id = IssueId(f"issue-{uuid.uuid4().hex[:8]}")
        issue = Issue(
            id=issue_id,
            title=title,
            description=description,
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        # 创建头脑风暴阶段（状态为 NEW，由 StageLoop 自动触发 AI）
        issue.create_stage(Stage.BRAINSTORM)
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
            "createdAt": issue.created_at.isoformat(),
            "archivedAt": issue.archived_at.isoformat() if issue.archived_at else None,
            "discardedAt": issue.discarded_at.isoformat() if issue.discarded_at else None,
            "workspace": {
                "id": issue.workspace.id if issue.workspace else None,
                "ready": issue.workspace.ready if issue.workspace else False,
                "workspace_path": issue.workspace.workspace_path if issue.workspace else "",
                "repo_url": issue.workspace.repo_url if issue.workspace else "",
                "branch": issue.workspace.branch if issue.workspace else "",
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
                }
                for stage, state in issue.stages.items()
            },
        }

    async def approve_stage(self, issue_id: str, stage: Stage, comment: str = "") -> Issue | None:
        """审批通过阶段"""
        issue = self._repo.get(IssueId(issue_id))
        if not issue:
            return None

        machine = self._get_machine(issue)
        machine.approve(stage, comment)  # → APPROVED
        machine.advance(stage)  # → 下一阶段 NEW

        logger.info(f"Issue {issue_id} 阶段 {stage.value} 审批通过")
        await self._broadcast("issue_updated", {"issue": self._issue_to_dict(issue)})
        return issue

    async def reject_stage(self, issue_id: str, stage: Stage, reason: str) -> Issue | None:
        """打回阶段"""
        issue = self._repo.get(IssueId(issue_id))
        if not issue:
            return None

        machine = self._get_machine(issue)
        machine.reject(stage, reason)  # → REJECTED

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

        machine = self._get_machine(issue)
        if not machine.can_trigger(stage):
            stage_state = issue.get_stage_state(stage)
            return {"status": "error", "message": f"当前状态 {stage_state.status.value} 不能触发 AI"}

        # 1. 准备 workspace
        if not await self._executor.prepare_workspace(issue, stage):
            return {"status": "error", "message": "workspace 准备失败"}

        # 2. executor 处理状态转换和执行
        result = await self._executor.execute_stage(issue, stage)
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
