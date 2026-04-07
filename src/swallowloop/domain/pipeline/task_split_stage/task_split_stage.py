"""任务拆分阶段"""

from ..stage import Stage


class TaskSplitStage(Stage):
    """任务拆分阶段 - AI 驱动"""

    def __init__(self):
        super().__init__(name="taskSplit")
        self.tasks = []
