"""环境准备 - 创建工作空间任务"""

import os
from ..task import Task, TaskResult


class EnvironmentCreateWorkspaceTask(Task):
    """环境准备 - 创建工作空间任务"""

    def __init__(self):
        super().__init__(
            name="创建工作空间",
            handler=self._execute,
            description="创建本地工作空间目录"
        )

    def _execute(self, context: dict) -> TaskResult:
        """执行创建工作空间"""
        workspace_path = context.get("workspace_path")
        if not workspace_path:
            return TaskResult(success=False, message="workspace_path 未指定")

        try:
            os.makedirs(workspace_path, exist_ok=True)
            return TaskResult(success=True, message=f"工作空间已创建: {workspace_path}")
        except Exception as e:
            return TaskResult(success=False, message=f"创建工作空间失败: {str(e)}")
