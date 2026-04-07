"""Issue 应用服务"""

import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...infrastructure.agent import BaseAgent
    from ...infrastructure.config import Config

from ...domain.model import Issue, IssueId, Stage, IssueStatus, IssueRunningStatus, Workspace, StageStatus, TodoStatus
from ...domain.repository import IssueRepository
from ...domain.pipeline import IssuePipeline
from ..dto import issue_to_dict, build_pipeline_info

logger = logging.getLogger(__name__)


class IssueService:
    """Issue 应用服务"""

    def __init__(self, repository: IssueRepository, executor: "ExecutorService", agent: "BaseAgent | None" = None, config: "Config | None" = None, ws_manager=None):
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
        await self._broadcast("issue_created", {"issue": issue_to_dict(issue)})
        return issue

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
        await self._broadcast("issue_updated", {"issue": issue_to_dict(issue)})
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
        await self._broadcast("issue_updated", {"issue": issue_to_dict(issue)})
        return issue

    async def trigger_ai(self, issue_id: str, stage: Stage) -> dict:
        """手动触发 AI 执行（委托给 ExecutorService 执行）

        流程：
        1. 设置基本 context（repo_url 等）
        2. 委托给 ExecutorService.execute_stage() 统一执行
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

        # 设置基本 context（Pipeline 自己会在 EnvironmentCreateWorkspaceTask 中创建 workspace）
        issue.pipeline.set_context_value("repo_url", issue.repo_url or "")
        issue.pipeline.set_context_value("branch", str(issue.id))
        issue.pipeline.set_context_value("stage", stage.value)
        issue.pipeline.set_context_value("issue_id", str(issue.id))

        # 委托给 ExecutorService 执行（ExecutorService 是唯一的执行引擎）
        return await self._executor.execute_stage(issue, stage)

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
