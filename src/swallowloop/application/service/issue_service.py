"""Issue 应用服务"""

import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .executor_service import ExecutorService

from ...domain.model import Issue, IssueId, Stage, IssueStatus
from ...domain.repository import IssueRepository
from ...domain.statemachine import StageStateMachine, LoggerHook

logger = logging.getLogger(__name__)


class IssueService:
    """Issue 应用服务"""

    def __init__(self, repository: IssueRepository, executor: "ExecutorService"):
        self._repo = repository
        self._executor = executor
        self._hooks = [LoggerHook()]

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
        logger.info(f"创建 Issue: {issue_id} - {title}，已创建头脑风暴阶段（NEW）")

        return issue

    async def approve_stage(self, issue_id: str, stage: Stage, comment: str = "") -> Issue | None:
        """审批通过阶段"""
        issue = self._repo.get(IssueId(issue_id))
        if not issue:
            return None

        machine = self._get_machine(issue)
        machine.approve(stage, comment)  # → APPROVED
        machine.advance(stage)  # → 下一阶段 NEW

        logger.info(f"Issue {issue_id} 阶段 {stage.value} 审批通过")
        return issue

    def reject_stage(self, issue_id: str, stage: Stage, reason: str) -> Issue | None:
        """打回阶段"""
        issue = self._repo.get(IssueId(issue_id))
        if not issue:
            return None

        machine = self._get_machine(issue)
        machine.reject(stage, reason)  # → REJECTED

        logger.info(f"Issue {issue_id} 阶段 {stage.value} 已打回: {reason}")
        return issue

    async def trigger_ai(self, issue_id: str, stage: Stage) -> dict:
        """手动触发 AI 执行

        注意：executor.execute_stage() 内部已经处理了状态转换
        (NEW → RUNNING → PENDING)，所以这里只需要触发即可
        """
        issue = self._repo.get(IssueId(issue_id))
        if not issue:
            return {"status": "error", "message": "Issue not found"}

        machine = self._get_machine(issue)
        if not machine.can_trigger(stage):
            stage_state = issue.get_stage_state(stage)
            return {"status": "error", "message": f"当前状态 {stage_state.status.value} 不能触发 AI"}

        # executor.execute_stage() 内部处理状态转换：NEW → RUNNING → PENDING
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

    def delete_issue(self, issue_id: str) -> bool:
        """删除 Issue"""
        return self._repo.delete(IssueId(issue_id))

    async def _advance_and_trigger(self, issue: Issue, current_stage: Stage) -> None:
        """进入下一阶段（不触发 AI，等待用户触发）"""
        # 计算下一阶段
        stages = list(Stage)
        current_idx = stages.index(current_stage)

        # 如果不是最后一个阶段
        if current_idx < len(stages) - 1:
            next_stage = stages[current_idx + 1]
            issue.create_stage(next_stage)  # 设为 NEW，不自动触发 AI
            self._repo.save(issue)
            logger.info(f"Issue {issue.id} 进入阶段: {next_stage.value}，等待触发")
