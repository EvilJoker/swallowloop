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

# 领域事件
from .event import DomainEvent

# Pipeline Bundle
from . import pipeline

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
    # 事件
    "DomainEvent",
    # Pipeline Bundle
    "pipeline",
]
