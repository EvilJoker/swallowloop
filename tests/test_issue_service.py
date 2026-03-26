"""Issue Service 测试"""

import pytest
from datetime import datetime

from swallowloop.domain.model import Issue, IssueId, Stage, StageStatus, IssueStatus, TodoStatus
from swallowloop.domain.repository import IssueRepository
from swallowloop.application.service import IssueService


class MockRepository(IssueRepository):
    """内存实现的 Issue 仓库"""

    def __init__(self):
        self._issues = {}

    def get(self, issue_id: IssueId) -> Issue | None:
        return self._issues.get(str(issue_id))

    def save(self, issue: Issue) -> None:
        self._issues[str(issue.id)] = issue

    def list_all(self) -> list[Issue]:
        return list(self._issues.values())

    def list_active(self) -> list[Issue]:
        return [i for i in self._issues.values() if i.is_active]

    def delete(self, issue_id: IssueId) -> bool:
        return self._issues.pop(str(issue_id), None) is not None

    def list_stages_by_status(self, status: StageStatus) -> list[tuple[Issue, Stage]]:
        result = []
        for issue in self.list_active():
            for stage, state in issue.stages.items():
                if state.status == status:
                    result.append((issue, stage))
        return result


class MockExecutor:
    """模拟 Executor - 正确模拟状态转换"""

    def __init__(self, repository=None, fail_probability: float = 0.0):
        """repository: 用于创建状态机
        fail_probability: 模拟失败概率 (0.0-1.0)
        """
        self._repo = repository
        self.called = []
        self.fail_probability = fail_probability

    def execute_stage(self, issue, stage):
        self.called.append((str(issue.id), stage))
        return {"status": "success", "output": "mock output"}

    async def execute_stage_async(self, issue, stage):
        self.called.append((str(issue.id), stage))

    async def execute_stage(self, issue, stage):
        """异步版本 - 正确模拟状态转换"""
        from swallowloop.domain.model import StageStatus
        from swallowloop.domain.statemachine import StageStateMachine

        self.called.append((str(issue.id), stage))

        if self._repo is None:
            # 没有 repository，无法执行状态转换
            return {"status": "success", "output": "mock output", "success": True, "error": None}

        # 模拟状态转换
        machine = StageStateMachine(issue, self._repo)

        # 获取当前状态
        state = issue.get_stage_state(stage)
        current_status = state.status

        # 根据当前状态进行转换
        if current_status == StageStatus.NEW:
            machine.start(stage)  # NEW → RUNNING
        elif current_status in [StageStatus.REJECTED, StageStatus.ERROR]:
            machine.retry(stage)  # REJECTED/ERROR → RUNNING

        # 模拟 AI 执行（短暂延迟）
        import asyncio
        await asyncio.sleep(0.01)  # 模拟短暂执行

        # 模拟执行结果
        import random
        success = random.random() > self.fail_probability

        if success:
            machine.execute(stage)  # RUNNING → PENDING
        else:
            machine.error(stage)  # RUNNING → ERROR

        return {
            "status": "success" if success else "error",
            "output": "mock output" if success else "mock error",
            "success": success,
            "error": None if success else "mock execution failed",
        }


@pytest.mark.asyncio
async def test_create_issue():
    """测试创建 Issue（NEW 状态，由 StageLoop 触发 AI）"""
    repo = MockRepository()
    executor = MockExecutor()
    service = IssueService(repo, executor)

    issue = await service.create_issue("测试 Issue", "测试描述")

    assert issue.title == "测试 Issue"
    assert issue.description == "测试描述"
    assert issue.status == IssueStatus.ACTIVE
    assert issue.current_stage == Stage.BRAINSTORM
    assert issue.id.value.startswith("issue-")
    # 创建后状态为 NEW（StageLoop 会自动触发 AI）
    assert issue.get_stage_state(Stage.BRAINSTORM).status == StageStatus.NEW


@pytest.mark.asyncio
async def test_approve_stage():
    """测试审批通过阶段"""
    repo = MockRepository()
    executor = MockExecutor()
    service = IssueService(repo, executor)

    issue = await service.create_issue("测试 Issue", "测试描述")
    issue_id = str(issue.id)

    # 创建后状态为 NEW，需要先执行 AI（模拟）
    # 直接使用状态机设置到 PENDING 状态
    from swallowloop.domain.statemachine import StageStateMachine
    machine = StageStateMachine(issue, repo)
    machine.start(Stage.BRAINSTORM)  # NEW → RUNNING
    # MockExecutor 不真正执行，所以直接设置为 PENDING
    issue.get_stage_state(Stage.BRAINSTORM).status = StageStatus.PENDING
    repo.save(issue)

    # 审批通过头脑风暴阶段
    updated = await service.approve_stage(issue_id, Stage.BRAINSTORM, "通过")

    assert updated.get_stage_state(Stage.BRAINSTORM).status == StageStatus.APPROVED
    # 审批通过后进入下一阶段，状态为 NEW（不自动触发 AI）
    assert updated.current_stage == Stage.PLAN_FORMED
    assert updated.get_stage_state(Stage.PLAN_FORMED).status == StageStatus.NEW


@pytest.mark.asyncio
async def test_reject_stage():
    """测试打回阶段"""
    repo = MockRepository()
    executor = MockExecutor()
    service = IssueService(repo, executor)

    issue = await service.create_issue("测试 Issue", "测试描述")
    issue_id = str(issue.id)

    # 创建后状态为 NEW，需要先设置为 PENDING
    from swallowloop.domain.statemachine import StageStateMachine
    machine = StageStateMachine(issue, repo)
    machine.start(Stage.BRAINSTORM)  # NEW → RUNNING
    issue.get_stage_state(Stage.BRAINSTORM).status = StageStatus.PENDING
    repo.save(issue)

    # 打回头脑风暴阶段
    updated = service.reject_stage(issue_id, Stage.BRAINSTORM, "方案不够详细")

    assert updated.get_stage_state(Stage.BRAINSTORM).status == StageStatus.REJECTED
    # 最新评论应该是 reject
    comments = updated.get_stage_state(Stage.BRAINSTORM).comments
    assert len(comments) == 1
    assert comments[0].action == "reject"
    assert comments[0].content == "方案不够详细"


@pytest.mark.asyncio
async def test_update_issue():
    """测试更新 Issue"""
    repo = MockRepository()
    executor = MockExecutor()
    service = IssueService(repo, executor)

    issue = await service.create_issue("原始标题", "原始描述")
    issue_id = str(issue.id)

    # 更新标题
    updated = service.update_issue(issue_id, title="新标题")
    assert updated.title == "新标题"
    assert updated.description == "原始描述"

    # 归档
    archived = service.archive_issue(issue_id)
    assert archived.status == IssueStatus.ARCHIVED
    assert archived.archived_at is not None


@pytest.mark.asyncio
async def test_delete_issue():
    """测试删除 Issue"""
    repo = MockRepository()
    executor = MockExecutor()
    service = IssueService(repo, executor)

    issue = await service.create_issue("测试 Issue", "测试描述")
    issue_id = str(issue.id)

    assert len(repo.list_all()) == 1

    success = service.delete_issue(issue_id)
    assert success is True
    assert len(repo.list_all()) == 0


def test_issue_aggregation():
    """测试 Issue 聚合根行为

    注意: Issue 对象本身不再有 approve_stage/start_stage/reject_stage 方法，
    这些状态转换现在由 StageStateMachine 处理。
    此测试保留用于验证 Issue 的基础属性和 get_latest_rejection 等方法。
    """
    issue = Issue(
        id=IssueId("test-issue"),
        title="测试",
        description="测试描述",
        status=IssueStatus.ACTIVE,
        current_stage=Stage.BRAINSTORM,
        created_at=datetime.now(),
    )

    # 初始所有阶段都是 NEW
    for stage in Stage:
        assert issue.get_stage_state(stage).status == StageStatus.NEW

    # 验证基础属性
    assert issue.current_stage == Stage.BRAINSTORM
    assert issue.is_active is True
    assert issue.status == IssueStatus.ACTIVE

    # 验证 get_latest_rejection 对没有评论的阶段返回 None
    rejection = issue.get_latest_rejection(Stage.BRAINSTORM)
    assert rejection is None


def test_todo_item():
    """测试 TodoItem"""
    from swallowloop.domain.model import TodoItem

    todo = TodoItem(id="t1", content="任务1")
    assert todo.status == TodoStatus.PENDING

    todo.mark_in_progress()
    assert todo.status == TodoStatus.IN_PROGRESS

    todo.mark_completed()
    assert todo.status == TodoStatus.COMPLETED

    todo2 = TodoItem(id="t2", content="任务2")
    todo2.mark_failed()
    assert todo2.status == TodoStatus.FAILED
