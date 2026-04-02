"""详细设计阶段"""

from ..stage import Stage


class DetailedDesignStage(Stage):
    """详细设计阶段 - AI 驱动"""

    def __init__(self):
        super().__init__(name="detailedDesign")
        self.tasks = []
