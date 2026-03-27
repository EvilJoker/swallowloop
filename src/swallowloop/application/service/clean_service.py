"""Clean Service - 定期清理已结束 Issue 的 DeerFlow 资源"""

import asyncio
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from ...domain.repository import IssueRepository
    from ...domain.model import Issue

logger = logging.getLogger(__name__)


class CleanService:
    """定期清理已结束 Issue 的 DeerFlow 资源"""

    def __init__(self, repository: "IssueRepository", base_url: str = "http://localhost:2026", interval_hours: int = 1):
        """
        Args:
            repository: Issue 仓库
            base_url: DeerFlow 服务地址
            interval_hours: 清理间隔（小时）
        """
        self._repo = repository
        self._base_url = base_url
        self._interval = timedelta(hours=interval_hours)
        self._client = httpx.AsyncClient()
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
        await self._client.aclose()
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
        if issue.status.value not in ["archived", "discarded"]:
            return False

        # 已清理过
        if issue.cleaned:
            return False

        # 清理间隔检查
        if issue.cleaned_at:
            time_since_cleanup = datetime.now() - issue.cleaned_at
            if time_since_cleanup < timedelta(hours=1):
                return False

        return True

    async def _cleanup_issue(self, issue: "Issue") -> None:
        """清理单个 Issue 的资源"""
        if not issue.workspace or not issue.workspace.id:
            logger.info(f"Issue {issue.id} 无 workspace，跳过")
            return

        thread_id = issue.workspace.id

        # 1. 调用 DeerFlow API 清理 Thread
        try:
            response = await self._client.delete(f"{self._base_url}/api/threads/{thread_id}")
            if response.status_code in [200, 204]:
                logger.info(f"DeerFlow Thread 清理成功: {thread_id}")
            else:
                logger.warning(f"DeerFlow Thread 清理失败: {response.status_code}")
        except Exception as e:
            logger.warning(f"DeerFlow Thread 清理异常: {e}")

        # 2. 删除本地目录
        workspace_path = Path(issue.workspace.workspace_path)
        if workspace_path.exists():
            try:
                # 只删除 thread 相关的目录
                thread_dir = workspace_path.parent.parent  # .deer-flow/threads/{thread_id}
                if thread_dir.exists():
                    shutil.rmtree(thread_dir)
                    logger.info(f"本地目录清理成功: {thread_dir}")
            except Exception as e:
                logger.warning(f"本地目录清理失败: {e}")

        # 3. 标记已清理
        issue.cleaned = True
        issue.cleaned_at = datetime.now()
        self._repo.save(issue)
        logger.info(f"Issue {issue.id} 清理标记完成")
