"""SwallowLoop - 燕子回环：围绕代码仓的智能维护Agent"""

# DDD 架构导出
from .domain.model import (
    Workspace,
    PullRequest,
    # Issue pipeline
    Stage,
    StageStatus,
    IssueStatus,
    TodoStatus,
    ExecutionState,
    Issue,
    IssueId,
    StageState,
    TodoItem,
    ReviewComment,
)
from .domain.repository import WorkspaceRepository, IssueRepository
from .application.service import IssueService, ExecutorService
from .application.dto import IssueDTO, WorkspaceDTO
from .infrastructure.config import Settings
from .infrastructure.persistence import JsonWorkspaceRepository, JsonIssueRepository

__version__ = "0.1.0"
__all__ = [
    # 版本
    "__version__",
    # DDD - 领域模型
    "Workspace",
    "PullRequest",
    # Issue pipeline
    "Stage",
    "StageStatus",
    "IssueStatus",
    "TodoStatus",
    "ExecutionState",
    "Issue",
    "IssueId",
    "StageState",
    "TodoItem",
    "ReviewComment",
    # DDD - 仓库接口
    "WorkspaceRepository",
    "IssueRepository",
    # DDD - 应用服务
    "IssueService",
    "ExecutorService",
    # DDD - DTO
    "IssueDTO",
    "WorkspaceDTO",
    # DDD - 基础设施
    "Settings",
    "JsonWorkspaceRepository",
    "JsonIssueRepository",
]
