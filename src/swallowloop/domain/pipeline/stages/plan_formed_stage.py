"""方案制定阶段"""

from ..stage import Stage


class PlanFormedStage(Stage):
    """方案制定阶段 - AI 驱动"""

    def __init__(self):
        super().__init__(name="planFormed")
        self.tasks = []
