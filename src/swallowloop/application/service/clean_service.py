"""Clean Service - 定期清理已结束 Issue 的 DeerFlow 资源"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from ...domain.model import IssueStatus
from ...infrastructure.agent import BaseAgent

if TYPE_CHECKING:
    from ...domain.repository import IssueRepository
    from ...domain.model import Issue

logger = logging.getLogger(__name__)


class CleanService:
    """定期清理已结束 Issue 的 DeerFlow 资源"""

    def __init__(
        self,
        repository: "IssueRepository",
        agent: BaseAgent,
        interval_hours: int = 1,
    ):
        """
        Args:
            repository: Issue 仓库
            agent: Agent 实例（用于调用 cleanup）
            interval_hours: 清理间隔（小时）
        """
        self._repo = repository
        self._agent = agent
        self._interval = timedelta(hours=interval_hours)
        self._running = False

    async def start(self) -> None:
        """启动清理任务"""
        self._running = True
        logger.info(f"CleanService 启动，清理间隔: {self._interval}")
        while self._running:
            try:
                await self._cleanup()
            except Exception as e:
                logger.error(f"清理任务执行失败: {e}")
            await asyncio.sleep(self._interval.total_seconds())

    async def stop(self) -> None:
        """停止清理任务"""
        self._running = False
        logger.info("CleanService 已停止")

    async def _cleanup(self) -> None:
        """执行清理"""
        # 扫描已结束但未清理的 Issue
        issues = self._repo.list_all()
        for issue in issues:
            if not self._should_cleanup(issue):
                continue

            try:
                await self._cleanup_issue(issue)
            except Exception as e:
                logger.error(f"清理 Issue {issue.id} 失败: {e}")

    def _should_cleanup(self, issue: "Issue") -> bool:
        """判断 Issue 是否应该清理"""
        # 必须已结束
        if issue.status not in [IssueStatus.ARCHIVED, IssueStatus.DISCARDED]:
            return False

        # 已清理过
        if issue.cleaned:
            return False

        # 清理间隔检查
        if issue.cleaned_at:
            time_since_cleanup = datetime.now() - issue.cleaned_at
            if time_since_cleanup < self._interval:
                return False

        return True

    async def _cleanup_issue(self, issue: "Issue") -> None:
        """清理单个 Issue 的资源"""
        if not issue.thread_id:
            logger.info(f"Issue {issue.id} 无 thread_id，跳过")
            return

        thread_id = issue.thread_id

        # 调用 Agent cleanup 接口
        await self._agent.cleanup(thread_id, issue.thread_path)

        # 标记已清理
        issue.cleaned = True
        issue.cleaned_at = datetime.now()
        self._repo.save(issue)
        logger.info(f"Issue {issue.id} 清理标记完成")
