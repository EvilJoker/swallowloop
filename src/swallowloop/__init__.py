"""SwallowLoop - 燕子回环：围绕代码仓的智能维护Agent"""

__version__ = "0.1.0"

# 领域层
from .domain import (
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
    IssueRepository,
    WorkspaceRepository,
    StageStateMachine,
    Hook,
    LoggerHook,
    DomainEvent,
)

# 应用层
from .application import IssueService, ExecutorService, StageLoop, ExecutorWorkerPool, IssueDTO, WorkspaceDTO

# 基础设施层
from .infrastructure import (
    InMemoryIssueRepository,
    BaseAgent,
    MockAgent,
    AgentResult,
    Config,
    LLMConfig,
    LLMProviderEnum,
    setup_logging,
    get_logger,
    SelfUpdater,
)

# 接口层
from .interfaces import app, run_server

__all__ = [
    # 版本
    "__version__",
    # 领域层 - 模型
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
    # 领域层 - 仓库
    "IssueRepository",
    "WorkspaceRepository",
    # 领域层 - 状态机
    "StageStateMachine",
    "Hook",
    "LoggerHook",
    # 领域层 - 事件
    "DomainEvent",
    # 应用层
    "IssueService",
    "ExecutorService",
    "StageLoop",
    "ExecutorWorkerPool",
    "IssueDTO",
    "WorkspaceDTO",
    # 基础设施层 - 持久化
    "InMemoryIssueRepository",
    # 基础设施层 - Agent
    "BaseAgent",
    "MockAgent",
    "AgentResult",
    # 基础设施层 - 配置
    "Config",
    "LLMConfig",
    "LLMProviderEnum",
    # 基础设施层 - 日志
    "setup_logging",
    "get_logger",
    # 基础设施层 - 自更新
    "SelfUpdater",
    # 接口层
    "app",
    "run_server",
]
