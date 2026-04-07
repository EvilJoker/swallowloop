"""头脑风暴阶段"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....infrastructure.agent import BaseAgent

from ..stage import Stage
from .brainstorm_task import BrainstormTask


class BrainstormStage(Stage):
    """头脑风暴阶段 - AI 驱动"""

    def __init__(self):
        super().__init__(name="brainstorm")
        self.tasks = [BrainstormTask()]
        self._agent: "BaseAgent | None" = None

    def set_agent(self, agent: "BaseAgent"):
        """注入 Agent"""
        self._agent = agent
        # 注入 agent 到 task
        if self.tasks:
            self.tasks[0].set_agent(agent)
