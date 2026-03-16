"""工作空间实体"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Workspace:
    """
    工作空间实体
    
    表示一个代码工作空间，包含本地路径和关联信息
    """
    id: str                              # 工作空间ID: issue{number}_{repo}_{date}
    issue_number: int                    # 关联的 Issue
    branch_name: str                     # 分支名
    path: Path                           # 本地路径
    pr_number: int | None = None         # PR 编号
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def is_active(self) -> bool:
        """检查工作空间是否仍然活跃"""
        return self.path.exists()
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if not isinstance(other, Workspace):
            return False
        return self.id == other.id
