"""领域事件基类"""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DomainEvent(ABC):
    """领域事件基类"""
    
    occurred_at: datetime = field(default_factory=datetime.now)
    
    @property
    def event_type(self) -> str:
        """事件类型"""
        return self.__class__.__name__
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
        }
