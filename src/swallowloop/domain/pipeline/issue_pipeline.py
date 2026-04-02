"""Issue Pipeline"""

from .pipeline import Pipeline
from .stages import (
    EnvironmentStage,
    BrainstormStage,
    PlanFormedStage,
    DetailedDesignStage,
    TaskSplitStage,
    ExecutionStage,
    UpdateDocsStage,
    SubmitStage,
)


class IssuePipeline(Pipeline):
    """Issue Pipeline - 包含所有 Stage"""

    def __init__(self):
        super().__init__(name="issue-pipeline")
        self.stages = [
            EnvironmentStage(),
            BrainstormStage(),
            PlanFormedStage(),
            DetailedDesignStage(),
            TaskSplitStage(),
            ExecutionStage(),
            UpdateDocsStage(),
            SubmitStage(),
        ]
