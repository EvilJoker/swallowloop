"""提交阶段"""

from ..stage import Stage


class SubmitStage(Stage):
    """提交阶段 - AI 驱动"""

    def __init__(self):
        super().__init__(
            name="submit",
            tasks=[],
            requires_approval=True,
        )
