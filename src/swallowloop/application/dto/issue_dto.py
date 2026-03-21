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
class WorkspaceDTO:
    """工作空间数据传输对象"""
    id: str
    issue_number: int
    branch_name: str
    path: Path
    pr_number: int | None = None
    created_at: datetime = field(default_factory=datetime.now)
