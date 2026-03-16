"""SwallowLoop - 燕子回环：围绕代码仓的智能维护Agent"""

# DDD 架构导出
from .domain.model import Task, TaskId, TaskState, TaskType, Workspace, Comment, PullRequest
from .domain.repository import TaskRepository, WorkspaceRepository
from .application.service import TaskService, ExecutionService
from .application.dto import IssueDTO, TaskDTO, WorkspaceDTO
from .infrastructure.config import Settings
from .infrastructure.persistence import JsonTaskRepository, JsonWorkspaceRepository
from .infrastructure.source_control import GitHubSourceControl
from .infrastructure.agent import Agent, IFlowAgent, AiderAgent

__version__ = "0.1.0"
__all__ = [
    # 版本
    "__version__",
    # DDD - 领域模型
    "Task",
    "TaskId",
    "TaskState",
    "TaskType",
    "Workspace",
    "Comment",
    "PullRequest",
    # DDD - 仓库接口
    "TaskRepository",
    "WorkspaceRepository",
    # DDD - 应用服务
    "TaskService",
    "ExecutionService",
    # DDD - DTO
    "IssueDTO",
    "TaskDTO",
    "WorkspaceDTO",
    # DDD - 基础设施
    "Settings",
    "JsonTaskRepository",
    "JsonWorkspaceRepository",
    "GitHubSourceControl",
    "Agent",
    "IFlowAgent",
    "AiderAgent",
]
