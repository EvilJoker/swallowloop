"""StageStateMachine 模块测试"""

import pytest
from datetime import datetime

from swallowloop.domain.model import Issue, IssueId, Stage, StageStatus, IssueStatus
from swallowloop.domain.statemachine import (
    StageStateMachine,
    InvalidTransitionError,
    ConcurrentModificationError,
    LoggerHook,
)
from tests.helpers import MockRepository


@pytest.fixture
def repo():
    return MockRepository()


@pytest.fixture
def issue(repo):
    issue = Issue(
        id=IssueId("test-issue"),
        title="测试",
        description="测试描述",
        status=IssueStatus.ACTIVE,
        current_stage=Stage.BRAINSTORM,
        created_at=datetime.now(),
    )
    repo.save(issue)
    return issue


class TestStageStateMachine:
    """StageStateMachine 模块功能测试"""

    def test_new_to_running(self, repo, issue):
        """NEW → RUNNING"""
        machine = StageStateMachine(issue, repo, [LoggerHook()])
        assert machine.start(Stage.BRAINSTORM) is True
        assert issue.get_stage_state(Stage.BRAINSTORM).status == StageStatus.RUNNING

    def test_running_to_pending(self, repo, issue):
        """RUNNING → PENDING"""
        machine = StageStateMachine(issue, repo)
        machine.start(Stage.BRAINSTORM)
        assert machine.execute(Stage.BRAINSTORM) is True
        assert issue.get_stage_state(Stage.BRAINSTORM).status == StageStatus.PENDING

    def test_invalid_transition(self, repo, issue):
        """非法转换应抛出异常"""
        machine = StageStateMachine(issue, repo)
        with pytest.raises(InvalidTransitionError):
            machine.approve(Stage.BRAINSTORM, "comment")

    def test_reject_and_retry(self, repo, issue):
        """REJECTED → RUNNING（重新触发）"""
        machine = StageStateMachine(issue, repo)
        machine.start(Stage.BRAINSTORM)
        machine.execute(Stage.BRAINSTORM)
        machine.reject(Stage.BRAINSTORM, "需要修改")

        assert machine.retry(Stage.BRAINSTORM) is True
        assert issue.get_stage_state(Stage.BRAINSTORM).status == StageStatus.RUNNING

    def test_advance_to_next_stage(self, repo, issue):
        """APPROVED → 下一阶段 NEW"""
        machine = StageStateMachine(issue, repo)
        machine.start(Stage.BRAINSTORM)
        machine.execute(Stage.BRAINSTORM)
        machine.approve(Stage.BRAINSTORM, "通过")

        assert machine.advance(Stage.BRAINSTORM) is True
        assert issue.current_stage == Stage.PLAN_FORMED
        assert issue.get_stage_state(Stage.PLAN_FORMED).status == StageStatus.NEW

    def test_version_increments_on_each_transition(self, repo, issue):
        """验证每次状态转换都会递增版本号"""
        machine = StageStateMachine(issue, repo)

        assert issue.version == 0

        machine.start(Stage.BRAINSTORM)
        assert issue.version == 1

        machine.execute(Stage.BRAINSTORM)
        assert issue.version == 2

        machine.approve(Stage.BRAINSTORM, "通过")
        assert issue.version == 3

    def test_can_trigger(self, repo, issue):
        """can_trigger 检查"""
        machine = StageStateMachine(issue, repo)

        assert machine.can_trigger(Stage.BRAINSTORM) is True

        machine.start(Stage.BRAINSTORM)
        assert machine.can_trigger(Stage.BRAINSTORM) is False

    def test_full_workflow(self, repo, issue):
        """完整工作流：NEW → RUNNING → PENDING → APPROVED → 下一阶段"""
        machine = StageStateMachine(issue, repo)

        machine.start(Stage.BRAINSTORM)
        assert issue.get_stage_state(Stage.BRAINSTORM).status == StageStatus.RUNNING

        machine.execute(Stage.BRAINSTORM)
        assert issue.get_stage_state(Stage.BRAINSTORM).status == StageStatus.PENDING

        machine.approve(Stage.BRAINSTORM, "设计合理")
        assert issue.get_stage_state(Stage.BRAINSTORM).status == StageStatus.APPROVED

        machine.advance(Stage.BRAINSTORM)
        assert issue.current_stage == Stage.PLAN_FORMED
        assert issue.get_stage_state(Stage.PLAN_FORMED).status == StageStatus.NEW

    def test_reject_workflow(self, repo, issue):
        """打回工作流"""
        machine = StageStateMachine(issue, repo)

        machine.start(Stage.BRAINSTORM)
        machine.execute(Stage.BRAINSTORM)
        machine.reject(Stage.BRAINSTORM, "逻辑有问题")

        assert issue.get_stage_state(Stage.BRAINSTORM).status == StageStatus.REJECTED

        machine.retry(Stage.BRAINSTORM)
        assert issue.get_stage_state(Stage.BRAINSTORM).status == StageStatus.RUNNING

        machine.execute(Stage.BRAINSTORM)
        machine.approve(Stage.BRAINSTORM, "已修改")
        machine.advance(Stage.BRAINSTORM)

        assert issue.current_stage == Stage.PLAN_FORMED

    def test_get_valid_transitions(self, repo, issue):
        """获取合法转换列表"""
        machine = StageStateMachine(issue, repo)

        transitions = machine.get_valid_transitions(Stage.BRAINSTORM)
        assert StageStatus.RUNNING in transitions

        machine.start(Stage.BRAINSTORM)
        transitions = machine.get_valid_transitions(Stage.BRAINSTORM)
        assert StageStatus.PENDING in transitions

    def test_running_to_error(self, repo, issue):
        """RUNNING → ERROR（AI 执行失败）"""
        machine = StageStateMachine(issue, repo)
        machine.start(Stage.BRAINSTORM)

        assert machine.error(Stage.BRAINSTORM) is True
        assert issue.get_stage_state(Stage.BRAINSTORM).status == StageStatus.ERROR

    def test_error_to_retry(self, repo, issue):
        """ERROR → RUNNING（重试）"""
        machine = StageStateMachine(issue, repo)
        machine.start(Stage.BRAINSTORM)
        machine.error(Stage.BRAINSTORM)

        assert machine.retry(Stage.BRAINSTORM) is True
        assert issue.get_stage_state(Stage.BRAINSTORM).status == StageStatus.RUNNING

    def test_approve_adds_comment(self, repo, issue):
        """approve 应添加评论"""
        machine = StageStateMachine(issue, repo)
        machine.start(Stage.BRAINSTORM)
        machine.execute(Stage.BRAINSTORM)

        machine.approve(Stage.BRAINSTORM, "设计合理")

        comments = issue.get_stage_state(Stage.BRAINSTORM).comments
        assert len(comments) == 1
        assert comments[0].action == "approve"
        assert comments[0].content == "设计合理"

    def test_reject_adds_reason(self, repo, issue):
        """reject 应添加原因"""
        machine = StageStateMachine(issue, repo)
        machine.start(Stage.BRAINSTORM)
        machine.execute(Stage.BRAINSTORM)

        machine.reject(Stage.BRAINSTORM, "逻辑有问题")

        comments = issue.get_stage_state(Stage.BRAINSTORM).comments
        assert len(comments) == 1
        assert comments[0].action == "reject"
        assert comments[0].content == "逻辑有问题"

    def test_invalid_transition_new_to_approve(self, repo, issue):
        """NEW 状态不能直接 APPROVE"""
        machine = StageStateMachine(issue, repo)
        with pytest.raises(InvalidTransitionError):
            machine.approve(Stage.BRAINSTORM, "comment")

    def test_invalid_transition_running_to_reject(self, repo, issue):
        """RUNNING 状态不能 REJECT"""
        machine = StageStateMachine(issue, repo)
        machine.start(Stage.BRAINSTORM)
        with pytest.raises(InvalidTransitionError):
            machine.reject(Stage.BRAINSTORM, "reason")

    def test_invalid_transition_approved_to_advance(self, repo, issue):
        """非 APPROVED 状态不能 advance"""
        machine = StageStateMachine(issue, repo)
        with pytest.raises(InvalidTransitionError):
            machine.advance(Stage.BRAINSTORM)

    def test_advance_at_last_stage(self, repo, issue):
        """最后一个阶段 advance 应返回 True"""
        # 创建一个在 SUBMIT 阶段的 issue
        issue.current_stage = Stage.SUBMIT
        issue.create_stage(Stage.SUBMIT)
        repo.save(issue)

        machine = StageStateMachine(issue, repo)
        machine.start(Stage.SUBMIT)
        machine.execute(Stage.SUBMIT)
        machine.approve(Stage.SUBMIT, "完成")

        # SUBMIT 是最后一个阶段，advance 直接返回 True
        assert machine.advance(Stage.SUBMIT) is True

    def test_can_trigger_rejected_and_error(self, repo, issue):
        """REJECTED 和 ERROR 状态可触发"""
        machine = StageStateMachine(issue, repo)

        # 设置为 REJECTED
        machine.start(Stage.BRAINSTORM)
        machine.execute(Stage.BRAINSTORM)
        machine.reject(Stage.BRAINSTORM, "reason")
        assert machine.can_trigger(Stage.BRAINSTORM) is True

        # 设置为 ERROR
        machine.retry(Stage.BRAINSTORM)
        machine.error(Stage.BRAINSTORM)
        assert machine.can_trigger(Stage.BRAINSTORM) is True

    def test_advance_creates_next_stage(self, repo, issue):
        """advance 应创建下一阶段"""
        machine = StageStateMachine(issue, repo)
        machine.start(Stage.BRAINSTORM)
        machine.execute(Stage.BRAINSTORM)
        machine.approve(Stage.BRAINSTORM, "通过")

        machine.advance(Stage.BRAINSTORM)

        # 下一阶段已创建
        assert Stage.PLAN_FORMED in issue.stages
        assert issue.current_stage == Stage.PLAN_FORMED
