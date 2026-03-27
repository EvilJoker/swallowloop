"""WorkerPool - AI 执行线程池"""
import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .executor_service import ExecutorService
    from ...domain.model import Stage
    from ...domain.repository import IssueRepository

logger = logging.getLogger(__name__)


class ExecutorWorkerPool:
    """Worker 线程池 - 管理 AI 执行并发"""

    def __init__(self, executor: "ExecutorService", max_workers: int = 3):
        self._executor = executor
        self._pool = ThreadPoolExecutor(max_workers=max_workers)
        self._running_tasks: dict[str, bool] = {}
        self._lock = threading.Lock()  # 保护 _running_tasks

    def submit(self, issue_id: str, stage: "Stage") -> bool:
        """提交执行任务到线程池

        Returns:
            True if submitted, False if already running
        """
        task_key = self._get_task_key(issue_id, stage)

        # 同步检查和添加，避免竞态条件
        with self._lock:
            if task_key in self._running_tasks:
                logger.warning(f"任务已在执行中: {task_key}")
                return False
            self._running_tasks[task_key] = True

        # 提交到线程池
        self._pool.submit(self._execute_in_executor, issue_id, stage)
        logger.info(f"提交任务到 WorkerPool: {task_key}, 当前运行中: {list(self._running_tasks.keys())}")
        return True

    def _execute_in_executor(self, issue_id: str, stage: "Stage") -> None:
        """在线程池中执行异步任务"""
        task_key = self._get_task_key(issue_id, stage)
        logger.info(f"WorkerPool 开始执行: {task_key}")
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # 获取 issue
                from swallowloop.domain.model import IssueId
                issue = self._executor._repo.get(IssueId(issue_id))
                if not issue:
                    logger.error(f"Issue 不存在: {issue_id}")
                    return

                # 执行阶段
                loop.run_until_complete(
                    self._executor.execute_stage(issue, stage)
                )
                logger.info(f"任务执行完成: {task_key}")
            finally:
                if loop:
                    loop.close()
        except Exception as e:
            logger.error(f"任务执行异常: {issue_id}/{stage.value} - {e}")
        finally:
            # 任务完成后同步移除
            with self._lock:
                self._running_tasks.pop(task_key, None)
            logger.info(f"任务已从运行列表移除: {task_key}, 剩余: {list(self._running_tasks.keys())}")

    def _get_task_key(self, issue_id: str, stage: "Stage") -> str:
        """获取任务唯一标识"""
        return f"{issue_id}_{stage.value}"

    def is_running(self, issue_id: str, stage: "Stage") -> bool:
        """检查任务是否正在执行"""
        task_key = self._get_task_key(issue_id, stage)
        with self._lock:
            return task_key in self._running_tasks

    def shutdown(self):
        """关闭线程池"""
        self._pool.shutdown(wait=True)
        logger.info("ExecutorWorkerPool 已关闭")
