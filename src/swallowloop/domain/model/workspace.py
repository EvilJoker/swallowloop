"""Workspace 领域模型"""

from dataclasses import dataclass, field


@dataclass
class Workspace:
    """
    Workspace information for DeerFlow integration

    Used for managing the DeerFlow Thread workspace corresponding to an Issue
    """
    id: str = ""  # = issue_id = thread_id
    ready: bool = False  # Whether workspace is ready
    workspace_path: str = ""  # Workspace path (host absolute path)
    repo_url: str = ""  # Repository URL
    branch: str = ""  # Branch name
    metadata: dict = field(default_factory=dict)  # Extra metadata
