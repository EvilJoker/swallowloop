"""Stage 和相关枚举定义"""

from enum import Enum


class Stage(Enum):
    """Issue 流水线阶段"""
    BRAINSTORM = "brainstorm"
    PLAN_FORMED = "planFormed"
    DETAILED_DESIGN = "detailedDesign"
    TASK_SPLIT = "taskSplit"
    EXECUTION = "execution"
    UPDATE_DOCS = "updateDocs"
    SUBMIT = "submit"


class StageStatus(Enum):
    """阶段状态"""
    PENDING = "pending"      # 待审批
    APPROVED = "approved"    # 已通过
    REJECTED = "rejected"    # 已打回
    RUNNING = "running"      # 执行中
    ERROR = "error"          # 异常


class IssueStatus(Enum):
    """Issue 状态"""
    ACTIVE = "active"        # 活跃
    ARCHIVED = "archived"    # 已归档
    DISCARDED = "discarded"  # 已废弃


class TodoStatus(Enum):
    """TODO 项状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionState(Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCESS = "success"
    FAILED = "failed"
