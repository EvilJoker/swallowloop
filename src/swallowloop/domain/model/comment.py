"""Comment 值对象"""

from dataclasses import dataclass, field
from datetime import datetime
import uuid

from .stage import Stage


# ========== 原有的 Comment（用于 GitHub PR 评论）==========
@dataclass(frozen=True)
class Comment:
    """
    评论值对象

    表示用户在 Issue 或 PR 上的评论
    """
    id: int
    body: str
    author: str
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.body:
            raise ValueError("评论内容不能为空")

    @property
    def is_bot_comment(self) -> bool:
        """是否为机器人评论"""
        return "SwallowLoop" in self.body


# ========== Issue 流水线审核评论 ==========
@dataclass
class ReviewComment:
    """流水线审核评论/意见"""
    id: str
    stage: Stage
    action: str  # "approve" | "reject"
    content: str
    created_at: datetime

    @classmethod
    def create(cls, stage: Stage, action: str, content: str) -> "ReviewComment":
        """创建新评论"""
        return cls(
            id=f"comment-{uuid.uuid4().hex[:8]}",
            stage=stage,
            action=action,
            content=content,
            created_at=datetime.now(),
        )
