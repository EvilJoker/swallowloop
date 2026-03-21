"""Issue 聚合根"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .stage import Stage, StageStatus, IssueStatus, TodoStatus, ExecutionState


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
    status: StageStatus = StageStatus.PENDING
    document: str = ""
    comments: list = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    todo_list: Optional[list[TodoItem]] = None
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
    stages: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.stages:
            self.stages = self._create_default_stages()

    def _create_default_stages(self) -> dict:
        """创建默认阶段"""
        return {s: StageState(stage=s) for s in Stage}

    def get_stage_state(self, stage: Stage) -> StageState:
        """获取阶段状态"""
        return self.stages[stage]

    def approve_stage(self, stage: Stage, comment: str = "") -> None:
        """审批通过阶段"""
        state = self.stages[stage]
        state.status = StageStatus.APPROVED
        state.completed_at = datetime.now()
        if comment:
            from .comment import Comment
            state.comments.append(Comment.create(stage, "approve", comment))

    def reject_stage(self, stage: Stage, reason: str) -> None:
        """打回阶段"""
        state = self.stages[stage]
        state.status = StageStatus.REJECTED
        if reason:
            from .comment import Comment
            state.comments.append(Comment.create(stage, "reject", reason))

    def start_stage(self, stage: Stage) -> None:
        """开始阶段执行"""
        state = self.stages[stage]
        state.status = StageStatus.RUNNING
        state.started_at = datetime.now()
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
