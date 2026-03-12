"""SwallowLoop - 燕子回环：围绕代码仓的智能维护Agent"""

from .config import Config
from .github_client import GitHubClient
from .models import Task, TaskState, TaskType, Workspace
from .orchestrator import Orchestrator
from .worker import TaskResult, Worker
from .workspace_manager import WorkspaceManager

__version__ = "0.1.0"
__all__ = [
    # 配置
    "Config",
    # 核心
    "Orchestrator",
    "Worker",
    # 模型
    "Task",
    "TaskState",
    "TaskType",
    "Workspace",
    "TaskResult",
    # GitHub
    "GitHubClient",
    # 工作空间
    "WorkspaceManager",
]
