"""环境准备 - 准备环境任务"""

from ..task import Task, TaskResult


class EnvironmentPrepareEnvTask(Task):
    """环境准备 - 准备环境任务"""

    def __init__(self):
        super().__init__(
            name="准备环境",
            handler=self._execute,
            description="准备环境（暂时跳过）"
        )

    def _execute(self, context: dict) -> TaskResult:
        """执行准备环境（暂时跳过）"""
        return TaskResult(success=True, message="准备环境任务暂时跳过")
