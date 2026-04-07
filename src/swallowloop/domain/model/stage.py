"""Stage 和相关枚举定义"""

from enum import Enum


class Stage(Enum):
    """Issue 流水线阶段（SDD 9 阶段）"""
    ENVIRONMENT = "environment"      # 环境准备
    SPECIFY = "specify"             # 规范定义
    CLARIFY = "clarify"             # 需求澄清
    PLAN = "plan"                   # 技术规划
    CHECKLIST = "checklist"         # 质量检查
    TASKS = "tasks"                 # 任务拆分
    ANALYZE = "analyze"             # 一致性分析
    IMPLEMENT = "implement"         # 编码实现
    SUBMIT = "submit"               # 提交发布


class StageStatus(Enum):
    """阶段状态"""
    NEW = "new"            # 新建
    RUNNING = "running"    # AI 执行中
    PENDING = "pending"    # 待审批
    APPROVED = "approved"   # 已通过
    REJECTED = "rejected"  # 已打回
    ERROR = "error"         # 异常


class IssueStatus(Enum):
    """Issue 状态"""
    ACTIVE = "active"        # 活跃
    ARCHIVED = "archived"    # 已归档
    DISCARDED = "discarded"  # 已废弃


class IssueRunningStatus(Enum):
    """Issue 泳道状态（人工管理）"""
    NEW = "new"                # 新建
    IN_PROGRESS = "in_progress"  # 进行中
    DONE = "done"              # 已完成


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
