"""Stage - Pipeline 中的阶段，包含多个 Task"""

from typing import Optional
from .task import Task, TaskResult


class Stage:
    """Stage 是 Pipeline 中的一个阶段，包含多个 Task"""

    def __init__(
        self,
        name: str,
        tasks: list[Task] = None,
        description: str = "",
    ):
        """
        Args:
            name: Stage 名称
            tasks: Task 列表
            description: Stage 描述
        """
        self.name = name
        self.tasks = tasks or []
        self.description = description
        self._last_result: TaskResult = TaskResult(success=True, message="")

    def execute(self, context: dict) -> tuple[dict, TaskResult]:
        """顺序执行所有 Task，如果某个 Task 返回失败则停止

        Args:
            context: 执行上下文

        Returns:
            (context, TaskResult) - TaskResult.success=True 表示全部成功，False 表示失败
        """
        result = context
        for task in self.tasks:
            result, task_result = task.execute(result)
            self._last_result = task_result
            if not task_result.success:
                # Task 执行失败，停止执行
                return result, task_result
        # 所有 Task 都成功
        return result, TaskResult(success=True, message=f"Stage '{self.name}' 执行完成")

    def add_task(self, task: Task) -> None:
        """添加 Task"""
        self.tasks.append(task)

    @property
    def last_result(self) -> TaskResult:
        """获取最后一个 Task 的执行结果"""
        return self._last_result

    def __repr__(self) -> str:
        return f"Stage(name={self.name!r}, tasks={len(self.tasks)})"
