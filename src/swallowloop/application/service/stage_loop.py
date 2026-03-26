"""StageLoop - 后台主循环，定期扫描并触发 NEW 状态的阶段"""
import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...domain.model import Stage, StageStatus
    from ...domain.repository import IssueRepository
    from ...infrastructure.executor.worker_pool import ExecutorWorkerPool

logger = logging.getLogger(__name__)


class StageLoop:
    """Stage 后台循环 - 定期扫描 NEW 状态并触发 AI 执行"""

    def __init__(
        self,
        repository: "IssueRepository",
        worker_pool: "ExecutorWorkerPool",
        interval: int = 5,
    ):
        self._repo = repository
        self._worker_pool = worker_pool
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
            return

        logger.info(f"发现 {len(all_triggerable)} 个可触发阶段的阶段")

        for issue, stage in all_triggerable:
            if self._can_trigger(issue, stage):
                logger.info(f"触发 AI 执行: {issue.id}/{stage.value}")
                self._worker_pool.submit(str(issue.id), stage)
            else:
                logger.debug(f"跳过（不可触发）: {issue.id}/{stage.value}")

    def _can_trigger(self, issue, stage) -> bool:
        """检查是否可以触发"""
        from ...domain.model import IssueStatus

        # Issue 必须是 ACTIVE
        if issue.status != IssueStatus.ACTIVE:
            return False

        # 必须是当前阶段才能触发
        if issue.current_stage != stage:
            return False

        # 没有正在执行的任务
        if self._worker_pool.is_running(str(issue.id), stage):
            return False

        return True
