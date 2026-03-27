"""Executor Service 接口定义"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....domain.model import Issue, Stage

class IExecutor(ABC):
    """Executor 服务接口"""

    @abstractmethod
    async def prepare_workspace(self, issue: "Issue", stage: "Stage") -> bool:
        """准备工作空间

        Returns:
            True if success, False otherwise
        """
        pass

    @abstractmethod
    async def execute_stage(self, issue: "Issue", stage: "Stage") -> dict:
        """执行阶段

        Returns:
            dict with keys: success, output, error
        """
        pass
