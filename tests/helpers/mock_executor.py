"""测试辅助 - Mock Executor"""

import random
import logging
from datetime import datetime
from swallowloop.domain.model import StageStatus

logger = logging.getLogger(__name__)


class MockExecutor:
    """模拟 Executor - 正确模拟状态转换"""

    def __init__(self, repository=None, fail_probability: float = 0.0):
        self._repo = repository
        self.called = []
        self.fail_probability = fail_probability

    def execute_stage(self, issue, stage):
        self.called.append((str(issue.id), stage))
        return {"status": "success", "output": "mock output"}

    async def prepare_workspace(self, issue, stage) -> bool:
        """模拟 prepare_workspace - 始终返回成功"""
        return True

    async def execute_stage_async(self, issue, stage):
        self.called.append((str(issue.id), stage))

    async def execute_stage(self, issue, stage):
        """异步版本 - 正确模拟状态转换"""
        self.called.append((str(issue.id), stage))

        if self._repo is None:
            return {"status": "success", "output": "mock output", "success": True, "error": None}

        state = issue.get_stage_state(stage)
        current_status = state.status

        if current_status == StageStatus.NEW:
            state.status = StageStatus.RUNNING
            state.started_at = datetime.now()
        elif current_status in [StageStatus.REJECTED, StageStatus.ERROR]:
            state.status = StageStatus.RUNNING
            state.started_at = datetime.now()

        import asyncio
        await asyncio.sleep(0.01)

        success = random.random() > self.fail_probability

        if success:
            state.status = StageStatus.PENDING
        else:
            state.status = StageStatus.ERROR

        return {
            "status": "success" if success else "error",
            "output": "mock output" if success else "mock error",
            "success": success,
            "error": None if success else "mock execution failed",
        }
