"""任务相关领域事件"""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from .base import DomainEvent

if TYPE_CHECKING:
    from ..model import TaskId, PullRequest, Comment


@dataclass
class TaskAssigned(DomainEvent):
    """任务已分配工作空间"""
    task_id: "TaskId"
    workspace_id: str
    
    def to_dict(self) -> dict:
        return super().to_dict() | {
            "task_id": str(self.task_id),
            "workspace_id": self.workspace_id,
        }


@dataclass
class TaskStarted(DomainEvent):
    """任务开始执行"""
    task_id: "TaskId"
    
    def to_dict(self) -> dict:
        return super().to_dict() | {
            "task_id": str(self.task_id),
        }


@dataclass
class TaskSubmitted(DomainEvent):
    """任务已提交 PR"""
    task_id: "TaskId"
    pull_request: "PullRequest"
    
    def to_dict(self) -> dict:
        return super().to_dict() | {
            "task_id": str(self.task_id),
            "pr_number": self.pull_request.number,
            "pr_url": self.pull_request.html_url,
        }


@dataclass
class TaskRevised(DomainEvent):
    """任务根据反馈修改"""
    task_id: "TaskId"
    comment: "Comment"
    
    def to_dict(self) -> dict:
        return super().to_dict() | {
            "task_id": str(self.task_id),
            "comment_id": self.comment.id,
        }


@dataclass
class TaskCompleted(DomainEvent):
    """任务完成"""
    task_id: "TaskId"
    
    def to_dict(self) -> dict:
        return super().to_dict() | {
            "task_id": str(self.task_id),
        }


@dataclass
class TaskAborted(DomainEvent):
    """任务终止"""
    task_id: "TaskId"
    reason: str
    
    def to_dict(self) -> dict:
        return super().to_dict() | {
            "task_id": str(self.task_id),
            "reason": self.reason,
        }
