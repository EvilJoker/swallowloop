"""测试辅助 - Mock Executor"""

import random
import logging
from datetime import datetime
from swallowloop.domain.model import StageStatus

logger = logging.getLogger(__name__)


class MockExecutor:
    """模拟 Executor - 正确模拟状态转换"""

    def __init__(self, repository=None, fail_probability: float = 0.0, agent=None):
        self._repo = repository
        self.called = []
        self.fail_probability = fail_probability
        # 用于模拟失败场景
        self._prepare_workspace_should_fail = False
        self._execute_should_fail = False
        self._execute_error_message = "mock execution failed"
        # 注入的 agent（用于 Pipeline 执行）
        self._agent = agent

    def get_issue(self, issue_id):
        """获取 Issue"""
        if self._repo is None:
            return None
        return self._repo.get(issue_id)

    def set_prepare_workspace_fail(self, should_fail: bool):
        """设置 prepare_workspace 是否失败"""
        self._prepare_workspace_should_fail = should_fail

    def set_execute_fail(self, should_fail: bool, error_message: str = "mock execution failed"):
        """设置 execute 是否失败"""
        self._execute_should_fail = should_fail
        self._execute_error_message = error_message

    def execute_stage(self, issue, stage):
        self.called.append((str(issue.id), stage))
        return {"status": "success", "output": "mock output"}

    async def prepare_workspace(self, issue, stage) -> bool:
        """模拟 prepare_workspace - 正确设置 thread_id 和 thread_path"""
        self.called.append(("prepare_workspace", str(issue.id), stage))
        if self._prepare_workspace_should_fail:
            return False

        # 模拟真实的 prepare_workspace 行为 - 设置 thread_id 和 thread_path
        if not issue.thread_id:
            issue.thread_id = f"thread-{issue.id}"
        if not issue.thread_path:
            issue.thread_path = f"/tmp/mock-workspace/{issue.thread_id}"

        return True

    async def execute_stage(self, issue, stage):
        """异步版本 - 正确模拟状态转换"""
        self.called.append((str(issue.id), stage))

        if self._execute_should_fail:
            state = issue.get_stage_state(stage)
            state.status = StageStatus.ERROR
            return {"success": False, "output": "", "error": self._execute_error_message}

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
        await asyncio.sleep(0.5)  # 足够长让测试验证 is_running 状态

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
