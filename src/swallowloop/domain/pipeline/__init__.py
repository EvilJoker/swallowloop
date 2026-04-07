"""Pipeline 模块 - 领域层的 Pipeline 实现"""

MODULE_NAME = "domain.pipeline"

from .task import Task, TaskResult, TaskStatus, TaskState
from .stage import Stage, StageStatus, StageState
from .pipeline import Pipeline, PipelineResult, PipelineStatus, PipelineState
from .context import PipelineContext
from .issue_pipeline import IssuePipeline, STAGE_INSTRUCTIONS

# Stage 导入
from .environment_stage.environment_stage import EnvironmentStage
from .brainstorm_stage.brainstorm_stage import BrainstormStage
from .plan_formed_stage.plan_formed_stage import PlanFormedStage
from .detailed_design_stage.detailed_design_stage import DetailedDesignStage
from .task_split_stage.task_split_stage import TaskSplitStage
from .execution_stage.execution_stage import ExecutionStage
from .update_docs_stage.update_docs_stage import UpdateDocsStage
from .submit_stage.submit_stage import SubmitStage

# Task 导入
from .environment_stage.environment_create_workspace_task import EnvironmentCreateWorkspaceTask
from .environment_stage.environment_clone_repo_task import EnvironmentCloneRepoTask
from .environment_stage.environment_switch_branch_task import EnvironmentSwitchBranchTask
from .environment_stage.environment_prepare_env_task import EnvironmentPrepareEnvTask

__all__ = [
    "MODULE_NAME",
    # 基类
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
    # Pipeline
    "IssuePipeline",
    "STAGE_INSTRUCTIONS",
    # Stages
    "EnvironmentStage",
    "BrainstormStage",
    "PlanFormedStage",
    "DetailedDesignStage",
    "TaskSplitStage",
    "ExecutionStage",
    "UpdateDocsStage",
    "SubmitStage",
    # Tasks
    "EnvironmentCreateWorkspaceTask",
    "EnvironmentCloneRepoTask",
    "EnvironmentSwitchBranchTask",
    "EnvironmentPrepareEnvTask",
]
