"""评论值对象"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Comment:
    """
    评论值对象
    
    表示用户在 Issue 上的评论
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
