"""Issue DTO"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class IssueDTO:
    """Issue 数据传输对象"""
    number: int
    title: str
    body: str
    state: str = "open"
    labels: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class TaskDTO:
    """任务数据传输对象"""
    task_id: str
    issue_number: int
    title: str
    description: str
    state: str
    branch_name: str
    task_type: str
    retry_count: int = 0
    submission_count: int = 0
    pr_url: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class WorkspaceDTO:
    """工作空间数据传输对象"""
    id: str
    issue_number: int
    branch_name: str
    path: Path
    pr_number: int | None = None
    created_at: datetime = field(default_factory=datetime.now)
