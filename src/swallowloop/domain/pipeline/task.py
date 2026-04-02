"""Task - Pipeline 中的最小执行单元"""

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class TaskResult:
    """Task 执行结果"""
    success: bool
    message: str
    data: dict = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}


class Task:
    """Task 是 Pipeline 中的最小执行单元"""

    def __init__(
        self,
        name: str,
        handler: Callable[[dict], TaskResult],
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

    def execute(self, context: dict) -> tuple[dict, TaskResult]:
        """执行 Task

        Args:
            context: 执行上下文

        Returns:
            (更新后的 context, TaskResult)
        """
        result = self.handler(context)
        if result is None:
            result = TaskResult(success=False, message="Task 未返回结果")
        return context, result

    def __repr__(self) -> str:
        return f"Task(name={self.name!r})"
