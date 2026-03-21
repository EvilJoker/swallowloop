"""Comment 值对象 - Issue 流水线审核评论"""

from dataclasses import dataclass
from datetime import datetime
import uuid

from .stage import Stage


@dataclass
class Comment:
    """评论/审核意见"""
    id: str
    stage: Stage
    action: str  # "approve" | "reject"
    content: str
    created_at: datetime

    @classmethod
    def create(cls, stage: Stage, action: str, content: str) -> "Comment":
        """创建新评论"""
        return cls(
            id=f"comment-{uuid.uuid4().hex[:8]}",
            stage=stage,
            action=action,
            content=content,
            created_at=datetime.now(),
        )
