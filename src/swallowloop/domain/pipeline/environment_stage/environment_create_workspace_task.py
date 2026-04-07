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
        """执行创建工作空间

        如果 thread_id 已存在，复用已有 workspace；否则调用 agent.prepare() 创建新的。
        """
        thread_id = context.get("thread_id")
        workspace_path = context.get("workspace_path")

        # 如果已有 thread_id，复用已有 workspace
        if thread_id and workspace_path:
            import os
            if os.path.exists(workspace_path):
                logger.info(f"工作空间已就绪（复用）: {workspace_path}")
                return TaskResult(
                    success=True,
                    message=f"工作空间已就绪（复用）: {workspace_path}",
                    data={"workspace_path": workspace_path, "thread_id": thread_id}
                )
            # workspace 不存在但有 thread_id，说明路径有问题，尝试重建
            logger.warning(f"workspace_path 存在但目录不存在，将重新创建: {workspace_path}")

        # 没有 thread_id 或 workspace，需要创建新的
        if not self._agent:
            return TaskResult(success=False, message="Agent 未配置，无法创建工作空间")

        issue_id = context.get("issue_id", "")
        agent_context = {
            "repo_url": context.get("repo_url", ""),
            "branch": context.get("branch", issue_id),
            "stage": context.get("stage", "environment"),
        }

        try:
            workspace_info = self._agent.prepare(issue_id, agent_context)
            logger.info(f"DeerFlow Thread 创建成功: thread_id={workspace_info.id}")

            return TaskResult(
                success=True,
                message=f"工作空间创建成功: {workspace_info.workspace_path}",
                data={
                    "workspace_path": workspace_info.workspace_path,
                    "thread_id": workspace_info.id,
                    "repo_url": workspace_info.repo_url,
                    "branch": workspace_info.branch,
                }
            )
        except Exception as e:
            logger.error(f"agent.prepare() 失败: {e}")
            return TaskResult(success=False, message=f"创建工作空间失败: {str(e)}")
