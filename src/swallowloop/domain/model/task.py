"""任务聚合根"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from transitions import Machine

from .enums import TaskState, TaskType
from .comment import Comment
from .pull_request import PullRequest
from .workspace import Workspace


@dataclass(frozen=True)
class TaskId:
    """任务ID值对象"""
    value: str
    
    def __str__(self) -> str:
        return self.value
    
    def __repr__(self) -> str:
        return f"TaskId({self.value})"


class Task:
    """
    任务聚合根 - 使用状态机管理状态流转
    
    状态流转图:
    new → assign → assigned → prepare → pending → start → in_progress
                                                              │
                    ┌─────────────────────────────────────────┼─────────────────┐
                    ↓                                         ↓                 ↓
                submitted ← submit                      pending ← retry    aborted ← abort
                    │                                         ↑
                    ↓                                         │
                completed ← complete                    revise
                    │
                    └──────→ pending (用户反馈)
    """
    
    # 状态转换定义
    TRANSITIONS = [
        # 正常流程
        {'trigger': 'assign', 'source': 'new', 'dest': 'assigned'},
        {'trigger': 'prepare', 'source': 'assigned', 'dest': 'pending'},
        {'trigger': 'start', 'source': 'pending', 'dest': 'in_progress'},
        {'trigger': 'submit', 'source': 'in_progress', 'dest': 'submitted'},
        {'trigger': 'complete', 'source': 'submitted', 'dest': 'completed'},
        
        # 异常处理
        {'trigger': 'retry', 'source': 'in_progress', 'dest': 'pending', 
         'conditions': 'can_retry'},
        {'trigger': 'abort', 'source': 'in_progress', 'dest': 'aborted'},
        {'trigger': 'abort', 'source': 'submitted', 'dest': 'aborted'},
        
        # 用户反馈
        {'trigger': 'revise', 'source': 'submitted', 'dest': 'pending'},
    ]
    
    def __init__(
        self,
        task_id: TaskId,
        issue_number: int,
        title: str,
        description: str = "",
        task_type: TaskType = TaskType.NEW_TASK,
        branch_name: str | None = None,
        repo_url: str | None = None,
        max_retries: int = 5,
        initial_state: str | None = None,
    ):
        # 基本属性
        self._id = task_id
        self._issue_number = issue_number
        self._title = title
        self._description = description
        self._task_type = task_type
        self._branch_name = branch_name or f"Issue{issue_number}"
        self._repo_url = repo_url
        
        # 关联实体
        self._workspace: Workspace | None = None
        self._pr: PullRequest | None = None
        self._comments: list[Comment] = []
        
        # 执行控制
        self._retry_count = 0
        self._max_retries = max_retries
        self._submission_count = 0
        
        # 时间戳
        self._created_at = datetime.now()
        self._updated_at = datetime.now()
        self._started_at: datetime | None = None
        
        # 领域事件
        self._events: list[Any] = []
        
        # 初始化状态机
        self._machine: Machine | None = None
        self._init_machine(initial_state)
    
    def _init_machine(self, initial_state: str | None = None) -> None:
        """初始化状态机"""
        if self._machine is None:
            self._machine = Machine(
                model=self,
                states=[s.value for s in TaskState],
                transitions=self.TRANSITIONS,
                initial=initial_state or TaskState.NEW.value,
                send_event=True,
                after_state_change='_update_timestamp',
                model_attribute='state',
            )
    
    def _update_timestamp(self, event) -> None:
        """状态变更后更新时间戳"""
        self._updated_at = datetime.now()
    
    # ==================== 业务行为 ====================
    
    def assign_workspace(self, workspace: Workspace) -> None:
        """分配工作空间"""
        from ..event import TaskAssigned
        
        self._init_machine()
        if self.state != TaskState.NEW.value:
            raise InvalidStateTransition(f"Cannot assign workspace from state: {self.state}")
        self._workspace = workspace
        self.assign()  # 状态机：new → assigned
        self._events.append(TaskAssigned(task_id=self._id, workspace_id=workspace.id))
    
    def mark_ready(self) -> None:
        """准备就绪（调用状态机 prepare 触发器）"""
        self._init_machine()
        self.prepare()  # 状态机：assigned → pending
    
    def begin_execution(self) -> None:
        """开始执行（调用状态机 start 触发器）"""
        from ..event import TaskStarted
        
        self._init_machine()
        self._started_at = datetime.now()
        self.start()  # 状态机：pending → in_progress
        self._events.append(TaskStarted(task_id=self._id))
    
    def submit_pr(self, pr: PullRequest) -> None:
        """提交 PR（调用状态机 submit 触发器）"""
        from ..event import TaskSubmitted
        
        self._init_machine()
        self._pr = pr
        self._submission_count += 1
        self.submit()  # 状态机：in_progress → submitted
        self._events.append(TaskSubmitted(task_id=self._id, pull_request=pr))
    
    def apply_revision(self, comment: Comment) -> None:
        """根据评论修改（调用状态机 revise 触发器）"""
        from ..event import TaskRevised
        
        self._init_machine()
        self._comments.append(comment)
        self._task_type = TaskType.REVISION
        self._retry_count = 0
        self.revise()  # 状态机：submitted → pending
        self._events.append(TaskRevised(task_id=self._id, comment=comment))
    
    def mark_completed(self) -> None:
        """完成任务（调用状态机 complete 触发器）"""
        self._init_machine()
        self.complete()  # 状态机：submitted → completed
    
    def can_retry(self, event=None) -> bool:
        """是否可以重试"""
        return self._retry_count < self._max_retries
    
    def increment_retry(self) -> None:
        """增加重试计数"""
        self._retry_count += 1
    
    def do_abort(self) -> None:
        """终止任务（调用状态机 abort 触发器）"""
        self._init_machine()
        self.abort()  # 状态机：in_progress → aborted
    
    def do_retry(self) -> None:
        """重试任务（调用状态机 retry 触发器）"""
        self._init_machine()
        self.retry()  # 状态机：in_progress → pending
    
    # ==================== 查询 ====================
    
    @property
    def id(self) -> TaskId:
        return self._id
    
    @property
    def issue_number(self) -> int:
        return self._issue_number
    
    @property
    def title(self) -> str:
        return self._title
    
    @property
    def description(self) -> str:
        return self._description
    
    @property
    def task_type(self) -> TaskType:
        return self._task_type
    
    @property
    def branch_name(self) -> str:
        return self._branch_name
    
    @property
    def repo_url(self) -> str | None:
        return self._repo_url
    
    @property
    def workspace(self) -> Workspace | None:
        return self._workspace
    
    @property
    def pr(self) -> PullRequest | None:
        return self._pr
    
    @property
    def comments(self) -> list[Comment]:
        return self._comments.copy()
    
    @property
    def latest_comment(self) -> Comment | None:
        return self._comments[-1] if self._comments else None
    
    @property
    def retry_count(self) -> int:
        return self._retry_count
    
    @property
    def submission_count(self) -> int:
        return self._submission_count
    
    @property
    def created_at(self) -> datetime:
        return self._created_at
    
    @property
    def updated_at(self) -> datetime:
        return self._updated_at
    
    @property
    def started_at(self) -> datetime | None:
        return self._started_at
    
    @property
    def is_active(self) -> bool:
        """任务是否活跃（未完成/未终止）"""
        return self.state not in (TaskState.COMPLETED.value, TaskState.ABORTED.value)
    
    @property
    def is_retryable(self) -> bool:
        """是否可重试"""
        return self._retry_count < self._max_retries
    
    @property
    def events(self) -> list[Any]:
        """获取领域事件"""
        return self._events.copy()
    
    def clear_events(self) -> None:
        """清除领域事件"""
        self._events.clear()
    
    def __repr__(self) -> str:
        return f"Task({self._id}, state={self.state}, issue=#{self._issue_number})"


class InvalidStateTransition(Exception):
    """无效状态转换异常"""
    pass
