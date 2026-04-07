"""Task - Pipeline 中的最小执行单元"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Any


class TaskState(Enum):
    """Task 执行状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskStatus:
    """Task 状态对象"""
    state: TaskState = TaskState.PENDING
    reason: str = ""
    extra: dict = field(default_factory=dict)

    def __str__(self) -> str:
        if self.reason:
            return f"{self.state.value.upper()} - {self.reason}"
        return self.state.value.upper()

    def is_pending(self) -> bool:
        return self.state == TaskState.PENDING

    def is_running(self) -> bool:
        return self.state == TaskState.RUNNING

    def is_completed(self) -> bool:
        return self.state == TaskState.COMPLETED

    def is_failed(self) -> bool:
        return self.state == TaskState.FAILED


@dataclass
class TaskResult:
    """Task 执行结果"""
    success: bool
    message: str
    data: dict = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}

    def to_status(self) -> TaskStatus:
        """转换为 TaskStatus"""
        return TaskStatus(
            state=TaskState.COMPLETED if self.success else TaskState.FAILED,
            reason=self.message,
            extra=self.data,
        )


class Task:
    """Task 是 Pipeline 中的最小执行单元"""

    def __init__(
        self,
        name: str,
        handler: Callable[[dict], TaskResult] = None,
        description: str = "",
    ):
        """
        Args:
            name: Task 名称
            handler: 执行函数，接收 context dict，返回 TaskResult
            description: Task 描述
        """
        self.name = name
        self.handler = handler
        self.description = description
        self._status = TaskStatus()
        self._result: TaskResult | None = None

    @property
    def status(self) -> TaskStatus:
        """获取当前状态"""
        return self._status

    def get_status(self) -> TaskStatus:
        """获取当前状态（兼容方法）"""
        return self._status

    @property
    def result(self) -> TaskResult | None:
        """获取执行结果"""
        return self._result

    def execute(self, context: dict) -> tuple[dict, TaskResult]:
        """执行 Task（支持同步/异步 handler）

        Args:
            context: 执行上下文

        Returns:
            (更新后的 context, TaskResult)
        """
        self._status = TaskStatus(state=TaskState.RUNNING)

        if self.handler is None:
            self._status = TaskStatus(state=TaskState.FAILED, reason="Task 未设置 handler")
            self._result = TaskResult(success=False, message="Task 未设置 handler")
            return context, self._result

        try:
            import asyncio
            import concurrent.futures

            # 先调用 handler 获取结果
            result = self.handler(context)

            # 检查结果是否是协程（适用于 bound async method 的情况）
            if asyncio.iscoroutine(result):
                # 异步 handler：使用线程池执行（避免 event loop 嵌套问题）
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    result = pool.submit(asyncio.run, result).result()

            if result is None:
                result = TaskResult(success=False, message="Task handler 未返回结果")

            # 用 result.data 更新 context
            if result.data:
                context.update(result.data)

            self._result = result
            self._status = result.to_status()
        except Exception as e:
            self._result = TaskResult(success=False, message=f"Task 执行异常: {str(e)}")
            self._status = TaskStatus(state=TaskState.FAILED, reason=f"Task 执行异常: {str(e)}")

        return context, self._result

    def reset(self):
        """重置状态和结果"""
        self._status = TaskStatus()
        self._result = None

    def __repr__(self) -> str:
        return f"Task(name={self.name!r}, status={self._status})"
