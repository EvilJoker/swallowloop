"""Pipeline - 流水线，包含多个 Stage"""

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from .stage import Stage
from .task import TaskResult


logger = logging.getLogger(__name__)


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
    ):
        """
        Args:
            name: Pipeline 名称
            stages: Stage 列表
            description: Pipeline 描述
        """
        self.name = name
        self.stages = stages or []
        self.description = description
        self._current_stage_index = 0
        self._last_result: Optional[TaskResult] = None

    def execute(self, initial_context: dict) -> Tuple[dict, PipelineResult]:
        """顺序执行所有 Stage，如果某个 Stage 中的 Task 返回失败则停止

        Args:
            initial_context: 初始上下文

        Returns:
            (所有 Stage 执行完成后的 context, PipelineResult)
        """
        context = initial_context.copy()
        self._current_stage_index = 0

        for i, stage in enumerate(self.stages):
            self._current_stage_index = i
            logger.info(f"Pipeline '{self.name}' executing stage {i + 1}/{len(self.stages)}: {stage.name}")

            context, stage_result = stage.execute(context)
            self._last_result = stage_result

            if not stage_result.success:
                logger.warning(f"Stage '{stage.name}' failed: {stage_result.message}")
                return context, PipelineResult(
                    success=False,
                    message=f"在 Stage '{stage.name}' 执行失败: {stage_result.message}",
                    failed_stage=stage.name,
                    failed_task=stage_result.message,
                )

            logger.info(f"Stage '{stage.name}' completed")

        self._current_stage_index = len(self.stages)
        logger.info(f"Pipeline '{self.name}' completed all {len(self.stages)} stages")
        return context, PipelineResult(success=True, message="Pipeline 执行完成")

    def execute_to_stage(self, initial_context: dict, target_stage_name: str) -> Tuple[dict, PipelineResult]:
        """执行到指定 stage 为止

        Args:
            initial_context: 初始上下文
            target_stage_name: 目标 stage 名称

        Returns:
            (context, PipelineResult)
        """
        context = initial_context.copy()
        self._current_stage_index = 0

        for i, stage in enumerate(self.stages):
            self._current_stage_index = i
            logger.info(f"Pipeline '{self.name}' executing stage {i + 1}/{len(self.stages)}: {stage.name}")

            context, stage_result = stage.execute(context)
            self._last_result = stage_result

            if not stage_result.success:
                logger.warning(f"Stage '{stage.name}' failed: {stage_result.message}")
                return context, PipelineResult(
                    success=False,
                    message=f"在 Stage '{stage.name}' 执行失败: {stage_result.message}",
                    failed_stage=stage.name,
                    failed_task=stage_result.message,
                )

            # 到达目标 stage，停止
            if stage.name == target_stage_name:
                logger.info(f"Pipeline '{self.name}' reached target stage: {target_stage_name}")
                return context, PipelineResult(success=True, message=f"已到达目标阶段: {stage.name}")

            logger.info(f"Stage '{stage.name}' completed")

        self._current_stage_index = len(self.stages)
        return context, PipelineResult(success=True, message="Pipeline 执行完成")

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
