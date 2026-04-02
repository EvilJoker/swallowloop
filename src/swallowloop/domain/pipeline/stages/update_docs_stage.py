"""更新文档阶段"""

from ..stage import Stage


class UpdateDocsStage(Stage):
    """更新文档阶段 - AI 驱动"""

    def __init__(self):
        super().__init__(name="updateDocs")
        self.tasks = []
