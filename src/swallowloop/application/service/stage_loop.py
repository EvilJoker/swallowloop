"""StageLoop - 后台主循环，定期扫描并触发 NEW 状态的阶段"""
import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...domain.model import Stage, StageStatus
    from ...domain.repository import IssueRepository
    from ...infrastructure.executor.worker_pool import ExecutorWorkerPool
    from .executor_service import ExecutorService

logger = logging.getLogger(__name__)


class StageLoop:
    """Stage 后台循环 - 定期扫描 NEW 状态并触发 AI 执行"""

    def __init__(
        self,
        repository: "IssueRepository",
        worker_pool: "ExecutorWorkerPool",
        executor: "ExecutorService",
        interval: int = 5,
    ):
        self._repo = repository
        self._worker_pool = worker_pool
        self._executor = executor
        self._interval = interval

    def start(self) -> None:
        """启动主循环（阻塞）"""
        logger.info(f"StageLoop 启动，间隔 {self._interval} 秒")
        while True:
            try:
                self.maintain()
            except Exception as e:
                logger.error(f"maintain 执行异常: {e}")
            time.sleep(self._interval)

    def maintain(self) -> None:
        """扫描并触发可执行 AI 的阶段（NEW/REJECTED/ERROR）"""
        from ...domain.model import Stage, StageStatus

        # 获取所有可触发状态的 (issue, stage) 对
        # NEW: 新建阶段
        # REJECTED: 被打回，需要重试
        # ERROR: 执行出错，需要重试
        triggerable_statuses = [StageStatus.NEW, StageStatus.REJECTED, StageStatus.ERROR]
        all_triggerable = []
        for status in triggerable_statuses:
            all_triggerable.extend(self._repo.list_stages_by_status(status))

        if not all_triggerable:
            logger.debug("无可触发的阶段")
            return

        logger.info(f"发现 {len(all_triggerable)} 个可触发阶段的阶段")

        for issue, stage in all_triggerable:
            can_trigger, reason = self._can_trigger(issue, stage)
            if can_trigger:
                # 1. 先准备 workspace (async)
                logger.info(f"准备 workspace: {issue.id}/{stage.value}")
                import asyncio
                if not asyncio.run(self._executor.prepare_workspace(issue, stage)):
                    logger.error(f"workspace 准备失败，跳过: {issue.id}/{stage.value}")
                    continue

                # 2. 提交到 worker pool
                logger.info(f"触发 AI 执行: {issue.id}/{stage.value}")
                submitted = self._worker_pool.submit(str(issue.id), stage)
                if not submitted:
                    logger.warning(f"提交失败（已在执行中）: {issue.id}/{stage.value}")
            else:
                logger.debug(f"跳过（不可触发）: {issue.id}/{stage.value}, 原因: {reason}")

    def _can_trigger(self, issue, stage) -> tuple[bool, str]:
        """检查是否可以触发

        Returns:
            (can_trigger, reason) 元组
        """
        from ...domain.model import IssueStatus

        # Issue 必须是 ACTIVE
        if issue.status != IssueStatus.ACTIVE:
            return False, f"Issue状态={issue.status.value}，不是ACTIVE"

        # 必须是当前阶段才能触发
        if issue.current_stage != stage:
            return False, f"current_stage={issue.current_stage.value}，stage={stage.value}"

        # 没有正在执行的任务
        if self._worker_pool.is_running(str(issue.id), stage):
            return False, "任务正在执行中"

        return True, ""
