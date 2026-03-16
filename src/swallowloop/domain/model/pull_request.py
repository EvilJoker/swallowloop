"""Pull Request 值对象"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class PullRequest:
    """
    Pull Request 值对象
    
    表示代码提交后的 PR 信息
    """
    number: int
    html_url: str
    branch_name: str
    title: str
    body: str = ""
    state: str = "open"
    created_at: datetime = field(default_factory=datetime.now)
