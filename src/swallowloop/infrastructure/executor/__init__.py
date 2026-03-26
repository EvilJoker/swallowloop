"""执行器"""

MODULE_NAME = "infrastructure.executor"

from .worker_pool import ExecutorWorkerPool

__all__ = ["MODULE_NAME", "ExecutorWorkerPool"]
