"""Pipeline 模块 - 领域层的 Pipeline 实现"""

MODULE_NAME = "domain.pipeline"

from .task import Task, TaskResult, TaskStatus, TaskState
from .stage import Stage, StageStatus, StageState
from .pipeline import Pipeline, PipelineResult, PipelineStatus, PipelineState
from .context import PipelineContext
from .issue_pipeline import IssuePipeline, STAGE_INSTRUCTIONS

__all__ = [
    "MODULE_NAME",
    # 基类（Pipeline 执行框架）
    "Task",
    "TaskResult",
    "TaskStatus",
    "TaskState",
    "Stage",
    "StageStatus",
    "StageState",
    "Pipeline",
    "PipelineResult",
    "PipelineStatus",
    "PipelineState",
    "PipelineContext",
    # IssuePipeline（门面类，应用层直接使用）
    "IssuePipeline",
    "STAGE_INSTRUCTIONS",
]
