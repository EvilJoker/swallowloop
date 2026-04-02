"""Pipeline 执行上下文"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PipelineContext:
    """Pipeline 执行上下文"""
    issue_id: str
    workspace_path: str
    repo_url: str
    repo_name: str = "repo"
    branch: str = "main"
    thread_id: str = ""
    stage: str = ""
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """转换为字典，用于传递给 Task handler"""
        return {
            "issue_id": self.issue_id,
            "workspace_path": self.workspace_path,
            "repo_url": self.repo_url,
            "repo_name": self.repo_name,
            "branch": self.branch,
            "thread_id": self.thread_id,
            "stage": self.stage,
            **self.extra,
        }
