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


class MockExecutor:
    """模拟 Executor"""

    def __init__(self):
        self.called = []

    def execute_stage(self, issue, stage):
        self.called.append((str(issue.id), stage))
        return {"status": "success", "output": "mock output"}

    async def execute_stage_async(self, issue, stage):
        self.called.append((str(issue.id), stage))

    async def execute_stage(self, issue, stage):
        """异步版本"""
        self.called.append((str(issue.id), stage))
        return {"status": "success", "output": "mock output"}


def test_create_issue():
    """测试创建 Issue"""
    repo = MockRepository()
    executor = MockExecutor()
    service = IssueService(repo, executor)

    issue = service.create_issue("测试 Issue", "测试描述")

    assert issue.title == "测试 Issue"
    assert issue.description == "测试描述"
    assert issue.status == IssueStatus.ACTIVE
    assert issue.current_stage == Stage.BRAINSTORM
    assert issue.id.value.startswith("issue-")


def test_approve_stage():
    """测试审批通过阶段"""
    repo = MockRepository()
    executor = MockExecutor()
    service = IssueService(repo, executor)

    issue = service.create_issue("测试 Issue", "测试描述")
    issue_id = str(issue.id)

    # 创建后状态为 NEW
    assert issue.get_stage_state(Stage.BRAINSTORM).status == StageStatus.NEW

    # 审批通过头脑风暴阶段
    import asyncio
    updated = asyncio.run(service.approve_stage(issue_id, Stage.BRAINSTORM, "通过"))

    assert updated.get_stage_state(Stage.BRAINSTORM).status == StageStatus.APPROVED
    # 审批通过后进入下一阶段，状态为 NEW（不自动触发 AI）
    assert updated.current_stage == Stage.PLAN_FORMED
    assert updated.get_stage_state(Stage.PLAN_FORMED).status == StageStatus.NEW


def test_reject_stage():
    """测试打回阶段"""
    repo = MockRepository()
    executor = MockExecutor()
    service = IssueService(repo, executor)

    issue = service.create_issue("测试 Issue", "测试描述")
    issue_id = str(issue.id)

    # 打回头脑风暴阶段
    updated = service.reject_stage(issue_id, Stage.BRAINSTORM, "方案不够详细")

    assert updated.get_stage_state(Stage.BRAINSTORM).status == StageStatus.REJECTED
    # 最新评论应该是 reject
    comments = updated.get_stage_state(Stage.BRAINSTORM).comments
    assert len(comments) == 1
    assert comments[0].action == "reject"
    assert comments[0].content == "方案不够详细"


def test_update_issue():
    """测试更新 Issue"""
    repo = MockRepository()
    executor = MockExecutor()
    service = IssueService(repo, executor)

    issue = service.create_issue("原始标题", "原始描述")
    issue_id = str(issue.id)

    # 更新标题
    updated = service.update_issue(issue_id, title="新标题")
    assert updated.title == "新标题"
    assert updated.description == "原始描述"

    # 归档
    archived = service.archive_issue(issue_id)
    assert archived.status == IssueStatus.ARCHIVED
    assert archived.archived_at is not None


def test_delete_issue():
    """测试删除 Issue"""
    repo = MockRepository()
    executor = MockExecutor()
    service = IssueService(repo, executor)

    issue = service.create_issue("测试 Issue", "测试描述")
    issue_id = str(issue.id)

    assert len(repo.list_all()) == 1

    success = service.delete_issue(issue_id)
    assert success is True
    assert len(repo.list_all()) == 0


def test_issue_aggregation():
    """测试 Issue 聚合根行为"""
    issue = Issue(
        id=IssueId("test-issue"),
        title="测试",
        description="测试描述",
        status=IssueStatus.ACTIVE,
        current_stage=Stage.BRAINSTORM,
        created_at=datetime.now(),
    )

    # 初始所有阶段都是 pending
    for stage in Stage:
        assert issue.get_stage_state(stage).status == StageStatus.PENDING

    # 审批通过 brainstorm
    issue.approve_stage(Stage.BRAINSTORM, "通过")
    assert issue.get_stage_state(Stage.BRAINSTORM).status == StageStatus.APPROVED

    # 进入下一阶段
    issue.start_stage(Stage.PLAN_FORMED)
    assert issue.current_stage == Stage.PLAN_FORMED
    assert issue.get_stage_state(Stage.PLAN_FORMED).status == StageStatus.RUNNING

    # 打回
    issue.reject_stage(Stage.PLAN_FORMED, "需要更详细")
    assert issue.get_stage_state(Stage.PLAN_FORMED).status == StageStatus.REJECTED

    # 获取最新打回原因
    rejection = issue.get_latest_rejection(Stage.PLAN_FORMED)
    assert rejection == "需要更详细"


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
