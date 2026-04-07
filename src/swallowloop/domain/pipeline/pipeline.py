"""Pipeline - 流水线，包含多个 Stage"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple

from .context import PipelineContext
from .stage import Stage, StageStatus
from .task import TaskResult


logger = logging.getLogger(__name__)


class PipelineState(Enum):
    """Pipeline 执行状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PipelineStatus:
    """Pipeline 状态对象"""
    state: PipelineState = PipelineState.PENDING
    reason: str = ""
    current_stage: str = ""  # 当前执行的 Stage 名称
    current_task: str = ""  # 当前执行的 Task 名称
    stages_status: list[StageStatus] = field(default_factory=list)  # 包含多个 StageStatus


@dataclass
class PipelineResult:
    """Pipeline 执行结果"""
    success: bool
    message: str
    failed_stage: Optional[str] = None
    failed_task: Optional[str] = None


class Pipeline:
    """Pipeline 流水线，包含多个 Stage，顺序执行"""

    def __init__(
        self,
        name: str,
        stages: list[Stage] = None,
        description: str = "",
        context: PipelineContext = None,
    ):
        """
        Args:
            name: Pipeline 名称
            stages: Stage 列表
            description: Pipeline 描述
            context: 阶段间共享上下文
        """
        self.name = name
        self.stages = stages or []
        self.description = description
        self.context = context or PipelineContext(issue_id="", workspace_path="", repo_url="")
        self._current_stage_index = 0
        self._last_result: Optional[TaskResult] = None
        self._status = PipelineStatus()  # Pipeline 状态对象

    @property
    def status(self) -> PipelineStatus:
        """获取当前状态"""
        return self._status

    def get_status(self) -> PipelineStatus:
        """获取当前状态（兼容方法）"""
        return self._status

    def execute(self, initial_context: dict | PipelineContext = None) -> Tuple[dict, PipelineResult]:
        """顺序执行所有 Stage，如果某个 Stage 中的 Task 返回失败则停止

        Args:
            initial_context: 初始上下文（dict 或 PipelineContext）

        Returns:
            (所有 Stage 执行完成后的 context dict, PipelineResult)
        """
        if isinstance(initial_context, dict):
            context_dict = initial_context.copy()
        else:
            context = initial_context or self.context
            context_dict = context.to_dict()
        self._current_stage_index = 0
        stages_status = []  # 收集所有 StageStatus

        # 更新 PipelineStatus 为 RUNNING
        self._status = PipelineStatus(
            state=PipelineState.RUNNING,
            reason="执行中",
            stages_status=stages_status
        )

        for i, stage in enumerate(self.stages):
            self._current_stage_index = i
            # 更新 Pipeline 当前 stage/task
            self._status.current_stage = stage.name
            self._status.current_task = ""
            logger.info(f"Pipeline '{self.name}' executing stage {i + 1}/{len(self.stages)}: {stage.name}")

            context_dict, stage_result = stage.execute(context_dict)
            self._last_result = stage_result
            # 收集 StageStatus
            stages_status.append(stage.status)

            if not stage_result.success:
                logger.warning(f"Stage '{stage.name}' failed: {stage_result.message}")
                # 更新 PipelineStatus 为 FAILED
                self._status = PipelineStatus(
                    state=PipelineState.FAILED,
                    reason=f"在 Stage '{stage.name}' 失败: {stage_result.message}",
                    current_stage=stage.name,
                    stages_status=stages_status
                )
                return context_dict, PipelineResult(
                    success=False,
                    message=f"在 Stage '{stage.name}' 执行失败: {stage_result.message}",
                    failed_stage=stage.name,
                    failed_task=stage_result.message,
                )

            logger.info(f"Stage '{stage.name}' completed")

        self._current_stage_index = len(self.stages)
        # 更新 PipelineStatus 为 COMPLETED
        self._status = PipelineStatus(
            state=PipelineState.COMPLETED,
            reason="执行完成",
            stages_status=stages_status
        )
        logger.info(f"Pipeline '{self.name}' completed all {len(self.stages)} stages")
        return context_dict, PipelineResult(success=True, message="Pipeline 执行完成")

    def execute_to_stage(self, initial_context: dict | PipelineContext = None, target_stage_name: str = "") -> Tuple[dict, PipelineResult]:
        """执行到指定 stage 为止

        Args:
            initial_context: 初始上下文（dict 或 PipelineContext）
            target_stage_name: 目标 stage 名称

        Returns:
            (context dict, PipelineResult)
        """
        if isinstance(initial_context, dict):
            context_dict = initial_context.copy()
        else:
            context = initial_context or self.context
            context_dict = context.to_dict()
        self._current_stage_index = 0
        stages_status = []  # 收集所有 StageStatus

        # 更新 PipelineStatus 为 RUNNING
        self._status = PipelineStatus(
            state=PipelineState.RUNNING,
            reason="执行中",
            stages_status=stages_status
        )

        for i, stage in enumerate(self.stages):
            self._current_stage_index = i
            # 更新 Pipeline 当前 stage/task
            self._status.current_stage = stage.name
            self._status.current_task = ""
            logger.info(f"Pipeline '{self.name}' executing stage {i + 1}/{len(self.stages)}: {stage.name}")

            context_dict, stage_result = stage.execute(context_dict)
            self._last_result = stage_result
            # 收集 StageStatus
            stages_status.append(stage.status)

            if not stage_result.success:
                logger.warning(f"Stage '{stage.name}' failed: {stage_result.message}")
                # 更新 PipelineStatus 为 FAILED
                self._status = PipelineStatus(
                    state=PipelineState.FAILED,
                    reason=f"在 Stage '{stage.name}' 失败: {stage_result.message}",
                    current_stage=stage.name,
                    stages_status=stages_status
                )
                return context_dict, PipelineResult(
                    success=False,
                    message=f"在 Stage '{stage.name}' 执行失败: {stage_result.message}",
                    failed_stage=stage.name,
                    failed_task=stage_result.message,
                )

            # 到达目标 stage，停止
            if stage.name == target_stage_name:
                logger.info(f"Pipeline '{self.name}' reached target stage: {target_stage_name}")
                # 更新 PipelineStatus 为 COMPLETED
                self._status = PipelineStatus(
                    state=PipelineState.COMPLETED,
                    reason=f"已到达目标阶段: {stage.name}",
                    current_stage=stage.name,
                    stages_status=stages_status
                )
                return context_dict, PipelineResult(success=True, message=f"已到达目标阶段: {stage.name}")

            logger.info(f"Stage '{stage.name}' completed")

        self._current_stage_index = len(self.stages)
        # 更新 PipelineStatus 为 COMPLETED
        self._status = PipelineStatus(
            state=PipelineState.COMPLETED,
            reason="执行完成",
            stages_status=stages_status
        )
        return context_dict, PipelineResult(success=True, message="Pipeline 执行完成")

    def current_stage(self) -> Optional[Stage]:
        """获取当前执行的 Stage"""
        if 0 <= self._current_stage_index < len(self.stages):
            return self.stages[self._current_stage_index]
        return None

    def current_stage_index(self) -> int:
        """获取当前 Stage 索引"""
        return self._current_stage_index

    def is_done(self) -> bool:
        """是否已完成所有 Stage"""
        return self._current_stage_index >= len(self.stages)

    def progress(self) -> tuple[int, int]:
        """获取进度 (current, total)"""
        return (self._current_stage_index + 1, len(self.stages))

    def add_stage(self, stage: Stage) -> None:
        """添加 Stage"""
        self.stages.append(stage)

    @property
    def last_result(self) -> Optional[TaskResult]:
        """获取最后一个 Task 的执行结果"""
        return self._last_result

    def __repr__(self) -> str:
        return f"Pipeline(name={self.name!r}, stages={len(self.stages)})"
