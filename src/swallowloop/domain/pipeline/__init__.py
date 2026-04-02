"""Pipeline 模块 - 领域层的 Pipeline 实现"""

MODULE_NAME = "domain.pipeline"

from .task import Task, TaskResult
from .stage import Stage
from .pipeline import Pipeline, PipelineResult
from .context import PipelineContext
from .issue_pipeline import IssuePipeline
from .tasks import (
    EnvironmentCreateWorkspaceTask,
    EnvironmentCloneRepoTask,
    EnvironmentSwitchBranchTask,
    EnvironmentPrepareEnvTask,
)
from .stages import (
    EnvironmentStage,
    BrainstormStage,
    PlanFormedStage,
    DetailedDesignStage,
    TaskSplitStage,
    ExecutionStage,
    UpdateDocsStage,
    SubmitStage,
)

__all__ = [
    "MODULE_NAME",
    # 基类
    "Task",
    "TaskResult",
    "Stage",
    "Pipeline",
    "PipelineResult",
    "PipelineContext",
    # Pipeline
    "IssuePipeline",
    # Tasks
    "EnvironmentCreateWorkspaceTask",
    "EnvironmentCloneRepoTask",
    "EnvironmentSwitchBranchTask",
    "EnvironmentPrepareEnvTask",
    # Stages
    "EnvironmentStage",
    "BrainstormStage",
    "PlanFormedStage",
    "DetailedDesignStage",
    "TaskSplitStage",
    "ExecutionStage",
    "UpdateDocsStage",
    "SubmitStage",
]
