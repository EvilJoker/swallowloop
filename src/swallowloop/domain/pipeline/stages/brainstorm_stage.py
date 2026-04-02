"""头脑风暴阶段"""

from ..stage import Stage


class BrainstormStage(Stage):
    """头脑风暴阶段 - AI 驱动"""

    def __init__(self):
        super().__init__(name="brainstorm")
        self.tasks = []
