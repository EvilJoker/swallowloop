"""执行阶段"""

from ..stage import Stage


class ExecutionStage(Stage):
    """执行阶段 - AI 驱动"""

    def __init__(self):
        super().__init__(name="execution")
        self.tasks = []
