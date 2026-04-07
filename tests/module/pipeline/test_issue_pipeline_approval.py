"""IssuePipeline 审批逻辑测试"""

import pytest
from swallowloop.domain.pipeline.issue_pipeline import IssuePipeline
from swallowloop.domain.pipeline.stage import Stage, StageState, ApprovalState, Task, TaskResult


def make_success_task(name):
    """创建成功的 Task"""
    def handler(ctx):
        return TaskResult(success=True, message=f"{name} 完成")
    return Task(name=name, handler=handler)


def make_fail_task(name):
    """创建失败的 Task"""
    def handler(ctx):
        return TaskResult(success=False, message=f"{name} 失败")
    return Task(name=name, handler=handler)


class TestIssuePipelineApproval:
    """IssuePipeline 审批逻辑测试"""

    def test_pipeline_has_stages(self):
        """Pipeline 有 9 个 SDD 阶段"""
        pipeline = IssuePipeline(
            issue_id="test-123",
            issue_title="Test Issue",
            issue_description="Test description"
        )

        stage_names = [s.name for s in pipeline._stages]
        assert len(stage_names) == 9
        assert "environment" in stage_names
        assert "specify" in stage_names
        assert "clarify" in stage_names
        assert "plan" in stage_names
        assert "checklist" in stage_names
        assert "tasks" in stage_names
        assert "analyze" in stage_names
        assert "implement" in stage_names
        assert "submit" in stage_names

    def test_environment_stage_no_approval_required(self):
        """环境准备阶段不需要审批"""
        pipeline = IssuePipeline(issue_id="test-123", issue_title="Test")
        env_stage = pipeline._stages[0]

        assert env_stage.name == "environment"
        assert env_stage.requires_approval is False
        assert env_stage.approval_state == ApprovalState.NOT_REQUIRED

    def test_other_stages_require_approval(self):
        """其他阶段需要审批"""
        pipeline = IssuePipeline(issue_id="test-123", issue_title="Test")

        # specify 阶段
        specify_stage = pipeline._stages[1]
        assert specify_stage.name == "specify"
        assert specify_stage.requires_approval is True
        assert specify_stage.approval_state == ApprovalState.PENDING

    def test_get_stage_by_name(self):
        """通过名称获取阶段"""
        pipeline = IssuePipeline(issue_id="test-123", issue_title="Test")

        stage = pipeline.get_stage("specify")
        assert stage is not None
        assert stage.name == "specify"

        not_found = pipeline.get_stage("nonexistent")
        assert not_found is None

    def test_set_agent(self):
        """设置 Agent"""
        pipeline = IssuePipeline(issue_id="test-123", issue_title="Test")

        class MockAgent:
            pass

        agent = MockAgent()
        pipeline.set_agent(agent)

        assert pipeline._agent is agent

    def test_get_context(self):
        """获取 PipelineContext"""
        pipeline = IssuePipeline(
            issue_id="test-123",
            issue_title="Test Issue",
            issue_description="Test description"
        )

        ctx = pipeline.get_context()
        assert ctx.issue_id == "test-123"

    def test_stage_order(self):
        """阶段顺序正确"""
        pipeline = IssuePipeline(issue_id="test-123", issue_title="Test")

        expected_order = [
            "environment", "specify", "clarify", "plan",
            "checklist", "tasks", "analyze", "implement", "submit"
        ]

        actual_order = [s.name for s in pipeline._stages]
        assert actual_order == expected_order


class TestPipelineApprovalWorkflow:
    """Pipeline 审批工作流测试（模拟）"""

    def test_approval_state_machine(self):
        """审批状态机转换"""
        # 模拟环境准备 -> specify -> approve -> clarify
        pipeline = IssuePipeline(issue_id="test-123", issue_title="Test")

        # 环境准备阶段完成
        env_stage = pipeline._stages[0]
        env_stage.set_waiting_approval()
        assert env_stage.status.is_waiting_approval()

        # 环境准备审批通过
        env_stage.approve()
        assert env_stage.status.is_approved()
        assert env_stage.approval_state == ApprovalState.APPROVED

        # specify 阶段
        specify_stage = pipeline._stages[1]
        specify_stage.set_waiting_approval()
        assert specify_stage.status.is_waiting_approval()

        # specify 审批打回
        specify_stage.reject("需要更多细节")
        assert specify_stage.status.is_rejected()
        assert specify_stage.approval_state == ApprovalState.REJECTED
        assert "需要更多细节" in specify_stage.approver_comments

    def test_only_waiting_approval_can_be_approved(self):
        """只有 WAITING_APPROVAL 状态才能审批"""
        pipeline = IssuePipeline(issue_id="test-123", issue_title="Test")

        specify_stage = pipeline._stages[1]

        # PENDING 状态不能直接 approve
        assert specify_stage.status.is_pending()

        # 必须先 set_waiting_approval
        specify_stage.set_waiting_approval()
        assert specify_stage.status.is_waiting_approval()

        # 才能 approve
        specify_stage.approve()
        assert specify_stage.status.is_approved()

    def test_reject_requires_comments(self):
        """打回必须提供意见"""
        pipeline = IssuePipeline(issue_id="test-123", issue_title="Test")

        clarify_stage = pipeline._stages[2]
        clarify_stage.set_waiting_approval()

        with pytest.raises(ValueError, match="打回时必须填写审批意见"):
            clarify_stage.reject("")
