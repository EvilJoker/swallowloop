"""领域层 - 核心业务，无外部依赖"""

MODULE_NAME = "domain"

# 模型
from .model import (
    Issue,
    IssueId,
    Stage,
    StageStatus,
    IssueStatus,
    TodoStatus,
    ExecutionState,
    StageState,
    TodoItem,
    ReviewComment,
    Workspace,
    PullRequest,
)

# 仓库接口
from .repository import IssueRepository, WorkspaceRepository

# 状态机
from .statemachine import (
    StageStateMachine,
    InvalidTransitionError,
    ConcurrentModificationError,
    Hook,
    LoggerHook,
    TransitionEvent,
)

# 领域事件
from .event import DomainEvent

__all__ = [
    "MODULE_NAME",
    # 模型
    "Issue",
    "IssueId",
    "Stage",
    "StageStatus",
    "IssueStatus",
    "TodoStatus",
    "ExecutionState",
    "StageState",
    "TodoItem",
    "ReviewComment",
    "Workspace",
    "PullRequest",
    # 仓库接口
    "IssueRepository",
    "WorkspaceRepository",
    # 状态机
    "StageStateMachine",
    "InvalidTransitionError",
    "ConcurrentModificationError",
    "Hook",
    "LoggerHook",
    "TransitionEvent",
    # 事件
    "DomainEvent",
]
