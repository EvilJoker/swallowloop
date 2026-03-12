"""数据模型定义 - 使用状态机"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from transitions import Machine


class TaskState(Enum):
    """任务状态"""
    NEW = "new"                       # 新接受
    ASSIGNED = "assigned"             # 已分配（工作空间已分配）
    PENDING = "pending"               # 待执行（等待Worker启动）
    IN_PROGRESS = "in_progress"       # 执行中
    SUBMITTED = "submitted"           # 已提交（PR已创建）
    COMPLETED = "completed"           # 已完成（Issue已关闭）
    ABORTED = "aborted"               # 异常终止


class TaskType(Enum):
    """任务类型"""
    NEW_TASK = "new_task"             # 新任务，需要 clone
    REVISION = "revision"             # 修改任务，在现有代码空间继续工作


class Task:
    """
    任务 - 使用状态机管理状态流转
    
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
        
        # 用户反馈
        {'trigger': 'revise', 'source': 'submitted', 'dest': 'pending'},
    ]
    
    def __init__(
        self,
        task_id: str,
        issue_number: int,
        title: str,
        description: str = "",
        task_type: TaskType = TaskType.NEW_TASK,
        branch_name: str | None = None,
        repo_url: str | None = None,
        max_retries: int = 5,
    ):
        # 基本属性
        self.id = task_id
        self.issue_number = issue_number
        self.title = title
        self.description = description
        self.task_type = task_type
        self.branch_name = branch_name or f"Issue{issue_number}"
        self.repo_url = repo_url  # Git 仓库地址
        
        # 代码空间
        self.workspace_id: str | None = None
        
        # PR 信息
        self.pr_number: int | None = None
        self.pr_url: str | None = None
        
        # 用户评论（不含 bot 评论）
        self.comments: list[dict] = []  # [{"id": 123, "body": "...", "created_at": "..."}]
        self.latest_comment: str | None = None  # 最新评论内容
        
        # 执行控制
        self.retry_count = 0
        self.max_retries = max_retries
        self.submission_count = 0  # 提交次数
        self.worker_pid: int | None = None
        
        # 时间戳
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.started_at: datetime | None = None
        
        # 初始化状态机
        self.machine = Machine(
            model=self,
            states=[s.value for s in TaskState],
            transitions=self.TRANSITIONS,
            initial=TaskState.NEW.value,
            send_event=True,
            after_state_change='_update_timestamp',
        )
    
    def _update_timestamp(self, event):
        """状态变更后更新时间戳"""
        self.updated_at = datetime.now()
    
    def can_retry(self, event) -> bool:
        """是否可以重试"""
        return self.retry_count < self.max_retries
    
    def increment_retry(self) -> None:
        """增加重试计数"""
        self.retry_count += 1
    
    def add_comment(self, comment_id: int, body: str, created_at: str) -> None:
        """添加用户评论"""
        comment = {
            "id": comment_id,
            "body": body,
            "created_at": created_at,
        }
        self.comments.append(comment)
        self.latest_comment = body
    
    def reset_for_revision(self) -> None:
        """为修改任务重置状态"""
        self.task_type = TaskType.REVISION
        self.retry_count = 0
    
    @property
    def is_active(self) -> bool:
        """任务是否活跃（未完成/未终止）"""
        return self.state not in (TaskState.COMPLETED.value, TaskState.ABORTED.value)
    
    @property
    def is_retryable(self) -> bool:
        """是否可重试"""
        return self.retry_count < self.max_retries
    
    def __repr__(self) -> str:
        return f"Task({self.id}, state={self.state}, issue=#{self.issue_number})"


@dataclass
class Workspace:
    """代码空间"""
    id: str                              # 工作空间ID: ws-{issue_number}
    issue_number: int                    # 关联的 Issue
    branch_name: str                     # 分支名
    path: Path                           # 本地路径
    pr_number: int | None = None         # PR 编号
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def is_active(self) -> bool:
        """检查工作空间是否仍然活跃"""
        return self.path.exists()
