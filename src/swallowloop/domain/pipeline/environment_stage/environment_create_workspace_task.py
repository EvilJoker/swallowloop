"""环境准备 - 创建工作空间任务"""

import logging
from typing import Optional
from ..task import Task, TaskResult

logger = logging.getLogger(__name__)


class EnvironmentCreateWorkspaceTask(Task):
    """环境准备 - 创建工作空间任务

    通过 Agent.prepare() 创建工作空间并获取 workspace_path
    """

    def __init__(self, agent=None):
        super().__init__(
            name="创建工作空间",
            handler=self._execute,
            description="通过 Agent.prepare() 创建工作空间"
        )
        self._agent = agent

    def set_agent(self, agent):
        """注入 Agent"""
        self._agent = agent

    def _execute(self, context: dict) -> TaskResult:
        """执行创建工作空间"""
        if not self._agent:
            return TaskResult(success=False, message="Agent 未注入")

        issue_id = context.get("issue_id", "")
        repo_url = context.get("repo_url", "")
        branch = context.get("branch", "main")

        try:
            # 调用 Agent.prepare() 创建 Thread/工作空间
            workspace_info = self._agent.prepare(
                issue_id=issue_id,
                context={
                    "repo_url": repo_url,
                    "branch": branch,
                    "stage": "environment",
                }
            )

            # 更新 context
            context["thread_id"] = workspace_info.id
            context["workspace_path"] = workspace_info.workspace_path

            logger.info(f"工作空间已创建: {workspace_info.workspace_path}")
            return TaskResult(
                success=True,
                message=f"工作空间已创建: {workspace_info.workspace_path}",
                data={"workspace_path": workspace_info.workspace_path, "thread_id": workspace_info.id}
            )
        except Exception as e:
            logger.error(f"创建工作空间失败: {e}")
            return TaskResult(success=False, message=f"创建工作空间失败: {str(e)}")
