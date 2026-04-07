"""环境准备阶段"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....infrastructure.agent import BaseAgent

from ..stage import Stage, StageState, StageStatus
from ..task import TaskResult
from .environment_create_workspace_task import EnvironmentCreateWorkspaceTask
from .environment_clone_repo_task import EnvironmentCloneRepoTask
from .environment_switch_branch_task import EnvironmentSwitchBranchTask
from .environment_prepare_env_task import EnvironmentPrepareEnvTask

logger = logging.getLogger(__name__)


class EnvironmentStage(Stage):
    """环境准备阶段"""

    def __init__(self):
        super().__init__(
            name="environment",
            tasks=[
                EnvironmentCreateWorkspaceTask(),
                EnvironmentCloneRepoTask(),
                EnvironmentSwitchBranchTask(),
                EnvironmentPrepareEnvTask(),
            ],
            requires_approval=False,
        )
        self._agent: "BaseAgent | None" = None

    def set_agent(self, agent: "BaseAgent"):
        """注入 Agent"""
        self._agent = agent

    def _inject_agent(self, task):
        """注入 agent 到 task"""
        if hasattr(task, 'set_agent') and self._agent:
            task.set_agent(self._agent)

    def execute_create_workspace(self, context: dict) -> tuple[dict, TaskResult]:
        """执行创建工作空间任务"""
        self._status = StageStatus(state=StageState.RUNNING, reason="创建工作空间")
        logger.info("执行 Task: 创建工作空间")

        # 使用 self.tasks 中已有的 task
        task = self.tasks[0]
        context, result = task.execute(context)
        self._last_result = result

        if result.success:
            self._status = StageStatus(
                state=StageState.COMPLETED,
                reason="创建工作空间完成",
                extra={"workspace_path": context.get("workspace_path", "")}
            )
        else:
            self._status = StageStatus(
                state=StageState.FAILED,
                reason=f"创建工作空间失败: {result.message}"
            )

        return context, result

    def execute_clone_repo(self, context: dict) -> tuple[dict, TaskResult]:
        """执行克隆仓库任务"""
        self._status = StageStatus(state=StageState.RUNNING, reason="克隆仓库")
        logger.info("执行 Task: 克隆仓库")

        # 使用 self.tasks 中已有的 task
        task = self.tasks[1]

        context, result = task.execute(context)
        self._last_result = result

        if result.success:
            self._status = StageStatus(
                state=StageState.COMPLETED,
                reason="克隆仓库完成",
                extra={"repo_path": context.get("repo_path", "")}
            )
        self._status = StageStatus(
            state=StageState.FAILED if not result.success else StageState.COMPLETED,
            reason=result.message
        )
        return context, result

    def execute_switch_branch(self, context: dict) -> tuple[dict, TaskResult]:
        """执行切换分支任务"""
        self._status = StageStatus(state=StageState.RUNNING, reason="切换分支")
        logger.info("执行 Task: 切换分支")

        # 使用 self.tasks 中已有的 task
        task = self.tasks[2]

        context, result = task.execute(context)
        self._last_result = result

        self._status = StageStatus(
            state=StageState.FAILED if not result.success else StageState.COMPLETED,
            reason=result.message
        )
        return context, result

    def execute_prepare_env(self, context: dict) -> tuple[dict, TaskResult]:
        """执行准备环境任务"""
        self._status = StageStatus(state=StageState.RUNNING, reason="准备环境")
        logger.info("执行 Task: 准备环境")

        # 使用 self.tasks 中已有的 task
        task = self.tasks[3]

        context, result = task.execute(context)
        self._last_result = result

        self._status = StageStatus(
            state=StageState.FAILED if not result.success else StageState.COMPLETED,
            reason=result.message
        )
        return context, result

    def execute(self, context: dict) -> tuple[dict, TaskResult]:
        """顺序执行环境准备的所有 Task

        Args:
            context: 执行上下文

        Returns:
            (context, TaskResult)
        """
        logger.info("开始执行环境准备阶段...")

        # 收集所有任务状态
        tasks_status = []

        # 执行创建工作空间
        context, result = self.execute_create_workspace(context)
        tasks_status.append(self.tasks[0].status)
        if not result.success:
            self._status = StageStatus(
                state=StageState.FAILED,
                reason=f"创建工作空间失败: {result.message}",
                tasks_status=tasks_status
            )
            return context, result

        # 执行克隆仓库
        context, result = self.execute_clone_repo(context)
        tasks_status.append(self.tasks[1].status)
        if not result.success:
            self._status = StageStatus(
                state=StageState.FAILED,
                reason=f"克隆仓库失败: {result.message}",
                tasks_status=tasks_status
            )
            return context, result

        # 执行切换分支
        context, result = self.execute_switch_branch(context)
        tasks_status.append(self.tasks[2].status)
        if not result.success:
            self._status = StageStatus(
                state=StageState.FAILED,
                reason=f"切换分支失败: {result.message}",
                tasks_status=tasks_status
            )
            return context, result

        # 执行准备环境
        context, result = self.execute_prepare_env(context)
        tasks_status.append(self.tasks[3].status)

        # 最终状态
        if result.success:
            self._status = StageStatus(
                state=StageState.COMPLETED,
                reason="环境准备完成",
                tasks_status=tasks_status
            )
        else:
            self._status = StageStatus(
                state=StageState.FAILED,
                reason=f"准备环境失败: {result.message}",
                tasks_status=tasks_status
            )

        logger.info("环境准备阶段执行完成")
        return context, result
