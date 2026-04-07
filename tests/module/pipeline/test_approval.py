"""Stage Approval 审批功能测试"""

import pytest
from datetime import datetime
from swallowloop.domain.pipeline.stage import (
    Stage,
    StageState,
    ApprovalState,
    Task,
    TaskResult,
)


class TestApprovalState:
    """ApprovalState 枚举测试"""

    def test_approval_state_values(self):
        """验证审批状态枚举值"""
        assert ApprovalState.NOT_REQUIRED.value == "not_required"
        assert ApprovalState.PENDING.value == "pending"
        assert ApprovalState.APPROVED.value == "approved"
        assert ApprovalState.REJECTED.value == "rejected"


class TestStageApproval:
    """Stage 审批功能测试"""

    def test_stage_requires_approval_default_true(self):
        """默认需要审批"""
        stage = Stage(name="test_stage")
        assert stage.requires_approval is True
        assert stage.approval_state == ApprovalState.PENDING

    def test_stage_not_requires_approval(self):
        """环境准备等阶段不需要审批"""
        stage = Stage(name="environment", requires_approval=False)
        assert stage.requires_approval is False
        assert stage.approval_state == ApprovalState.NOT_REQUIRED

    def test_approve_without_comments(self):
        """审批通过（无意见）"""
        stage = Stage(name="test_stage")
        stage.approve()

        assert stage.approval_state == ApprovalState.APPROVED
        assert stage.approved_at is not None
        assert stage.approver_comments == ""  # 通过时意见可选
        assert stage.status.state == StageState.APPROVED

    def test_approve_with_comments(self):
        """审批通过（有意见）"""
        stage = Stage(name="test_stage")
        stage.approve("looks good!")

        assert stage.approval_state == ApprovalState.APPROVED
        assert stage.approved_at is not None
        assert stage.approver_comments == "looks good!"

    def test_reject_requires_comments(self):
        """打回必须填写意见"""
        stage = Stage(name="test_stage")

        with pytest.raises(ValueError, match="打回时必须填写审批意见"):
            stage.reject("")

    def test_reject_with_comments(self):
        """打回（有意见）"""
        stage = Stage(name="test_stage")
        stage.reject("needs more work")

        assert stage.approval_state == ApprovalState.REJECTED
        assert stage.approved_at is not None
        assert stage.approver_comments == "needs more work"
        assert stage.status.state == StageState.REJECTED
        assert "needs more work" in stage.status.reason

    def test_set_waiting_approval(self):
        """设置等待审批状态"""
        stage = Stage(name="test_stage")
        stage.set_waiting_approval()

        assert stage.approval_state == ApprovalState.PENDING
        assert stage.status.state == StageState.WAITING_APPROVAL

    def test_set_waiting_approval_with_reason(self):
        """设置等待审批状态（自定义原因）"""
        stage = Stage(name="test_stage")
        stage.set_waiting_approval("DeerFlow 执行完成")

        assert stage.status.state == StageState.WAITING_APPROVAL
        assert stage.status.reason == "DeerFlow 执行完成"


class TestStageStateEx:
    """StageState 扩展状态测试"""

    def test_stage_state_waiting_approval(self):
        """WAITING_APPROVAL 状态"""
        assert StageState.WAITING_APPROVAL.value == "waiting_approval"

    def test_stage_state_approved(self):
        """APPROVED 状态"""
        assert StageState.APPROVED.value == "approved"

    def test_stage_state_rejected(self):
        """REJECTED 状态"""
        assert StageState.REJECTED.value == "rejected"

    def test_is_waiting_approval(self):
        """is_waiting_approval 方法"""
        stage = Stage(name="test_stage")
        assert stage.status.is_waiting_approval() is False

        stage.set_waiting_approval()
        assert stage.status.is_waiting_approval() is True

    def test_is_approved(self):
        """is_approved 方法"""
        stage = Stage(name="test_stage")
        assert stage.status.is_approved() is False

        stage.approve()
        assert stage.status.is_approved() is True

    def test_is_rejected(self):
        """is_rejected 方法"""
        stage = Stage(name="test_stage")
        assert stage.status.is_rejected() is False

        stage.reject("failed")
        assert stage.status.is_rejected() is True


class TestApprovalWorkflow:
    """审批工作流测试"""

    def test_full_approval_workflow(self):
        """完整审批工作流"""
        # 1. 阶段执行完成，设置等待审批
        stage = Stage(name="specify_stage")
        stage.set_waiting_approval()

        assert stage.status.is_waiting_approval()

        # 2. 用户审批通过
        stage.approve("approved!")

        assert stage.status.is_approved()
        assert stage.approval_state == ApprovalState.APPROVED
        assert stage.approver_comments == "approved!"

    def test_full_reject_workflow(self):
        """完整打回工作流"""
        # 1. 阶段执行完成，设置等待审批
        stage = Stage(name="specify_stage")
        stage.set_waiting_approval()

        assert stage.status.is_waiting_approval()

        # 2. 用户打回
        stage.reject("please clarify the requirements")

        assert stage.status.is_rejected()
        assert stage.approval_state == ApprovalState.REJECTED
        assert "please clarify" in stage.approver_comments

    def test_environment_stage_no_approval_needed(self):
        """环境准备阶段不需要审批"""
        stage = Stage(name="environment", requires_approval=False)

        assert stage.approval_state == ApprovalState.NOT_REQUIRED
        assert stage.status.state == StageState.PENDING
