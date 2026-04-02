"""Issue 聚合根"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from .stage import Stage, StageStatus, IssueStatus, IssueRunningStatus, TodoStatus, ExecutionState
from .workspace import Workspace


@dataclass
class TodoItem:
    """TODO 项"""
    id: str
    content: str
    status: TodoStatus = TodoStatus.PENDING

    def mark_in_progress(self):
        self.status = TodoStatus.IN_PROGRESS

    def mark_completed(self):
        self.status = TodoStatus.COMPLETED

    def mark_failed(self):
        self.status = TodoStatus.FAILED


@dataclass
class StageState:
    """阶段状态"""
    stage: Stage
    status: StageStatus = StageStatus.NEW
    document: str = ""
    stage_content: str = ""  # 阶段生成的内容
    result_content: str = ""  # Agent 执行结果
    comments: list = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    todo_list: Optional[List[TodoItem]] = None
    progress: Optional[int] = None
    execution_state: Optional[ExecutionState] = None


@dataclass
class IssueId:
    """Issue ID 值对象"""
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass
class Issue:
    """Issue 聚合根"""
    id: IssueId
    title: str
    description: str
    status: IssueStatus
    current_stage: Stage
    created_at: datetime
    archived_at: Optional[datetime] = None
    discarded_at: Optional[datetime] = None
    version: int = 0  # 乐观锁版本号
    stages: dict = field(default_factory=dict)

    # Workspace 别名 - 使用 domain.model.workspace.Workspace
    workspace: Optional[Workspace] = None
    repo_url: str = ""  # 代码仓库地址（默认从 Settings 获取）
    cleaned: bool = False  # 是否已清理
    cleaned_at: Optional[datetime] = None  # 上次清理时间

    # DeerFlow Thread 信息
    thread_id: str = ""  # DeerFlow 返回的 UUID，保留历史
    thread_path: str = ""  # workspace 路径，保留历史

    # 状态机字典（由 init_state_models 初始化）
    state_models: dict = field(default_factory=dict, init=False)

    # 泳道状态（人工管理）
    running_status: IssueRunningStatus = IssueRunningStatus.NEW

    def __post_init__(self):
        if not self.stages:
            self.stages = self._create_default_stages()

    def init_state_models(self, services: "StageServices") -> None:
        """
        初始化所有阶段的状态机

        Args:
            services: StageServices 服务容器
        """
        from ..statemachine.stage_state_model_factory import create_stage_state_models
        self.state_models = create_stage_state_models(self, services)

    def _create_default_stages(self) -> dict:
        """创建默认阶段"""
        stages = {s: StageState(stage=s) for s in Stage}
        # 环境准备阶段设置默认任务列表
        env_todos = [
            TodoItem(id="env-1", content="创建工作空间"),
            TodoItem(id="env-2", content="Clone 代码库"),
            TodoItem(id="env-3", content="切换分支"),
            TodoItem(id="env-4", content="准备环境"),
        ]
        stages[Stage.ENVIRONMENT].todo_list = env_todos
        return stages

    def get_stage_state(self, stage: Stage) -> StageState:
        """获取阶段状态"""
        return self.stages[stage]

    def create_stage(self, stage: Stage) -> None:
        """创建阶段（新建状态）"""
        state = self.stages[stage]
        state.status = StageStatus.NEW
        self.current_stage = stage

    def get_latest_rejection(self, stage: Stage) -> Optional[str]:
        """获取最新的打回原因"""
        state = self.stages[stage]
        for comment in reversed(state.comments):
            if comment.action == "reject":
                return comment.content
        return None

    @property
    def is_active(self) -> bool:
        """Issue 是否活跃"""
        return self.status == IssueStatus.ACTIVE

    def mark_in_progress(self) -> None:
        """标记为进行中"""
        self.running_status = IssueRunningStatus.IN_PROGRESS

    def mark_done(self) -> None:
        """标记为已完成"""
        self.running_status = IssueRunningStatus.DONE

    def is_in_progress(self) -> bool:
        """是否进行中"""
        return self.running_status == IssueRunningStatus.IN_PROGRESS
