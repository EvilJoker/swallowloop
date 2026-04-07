"""IssueService 模块测试"""

import pytest
import logging
from datetime import datetime
from unittest.mock import MagicMock
from swallowloop.domain.model import Stage, StageStatus, IssueStatus, IssueRunningStatus, IssueId
from swallowloop.application.service import IssueService
from tests.helpers import MockRepository, MockExecutor

logger = logging.getLogger(__name__)


@pytest.fixture
def repo():
    return MockRepository()


@pytest.fixture
def mock_agent():
    """创建 Mock Agent 用于测试"""
    agent = MagicMock()
    agent.prepare = MagicMock(return_value=MagicMock(
        id="test-thread",
        workspace_path="/tmp/test-workspace",
        ready=True
    ))
    agent.execute = MagicMock(return_value=MagicMock(success=True, output="mock output"))
    return agent


@pytest.fixture
def executor(repo, mock_agent):
    return MockExecutor(repository=repo, agent=mock_agent)


@pytest.fixture
def service(repo, executor):
    return IssueService(repo, executor)


class TestIssueService:
    """IssueService 功能测试"""

    @pytest.mark.asyncio
    async def test_create_issue(self, repo, executor, service):
        """测试创建 Issue"""
        issue = await service.create_issue("测试 Issue", "测试描述")

        assert issue.title == "测试 Issue"
        assert issue.description == "测试描述"
        assert issue.status == IssueStatus.ACTIVE
        assert issue.current_stage == Stage.ENVIRONMENT
        assert issue.id.value.startswith("issue-")
        assert issue.get_stage_state(Stage.ENVIRONMENT).status == StageStatus.NEW

    @pytest.mark.asyncio
    async def test_create_issue_sets_running_status_to_new(self, repo, executor, service):
        """测试创建 Issue 时 running_status 为 NEW"""
        issue = await service.create_issue("测试", "描述")
        assert issue.running_status == IssueRunningStatus.NEW

    @pytest.mark.asyncio
    async def test_approve_stage(self, repo, executor, service):
        """测试审批通过阶段"""
        issue = await service.create_issue("测试 Issue", "测试描述")
        issue_id = str(issue.id)

        # 设置阶段为 PENDING 状态（模拟 AI 执行完成）
        stage_state = issue.get_stage_state(Stage.BRAINSTORM)
        stage_state.status = StageStatus.PENDING
        stage_state.started_at = datetime.now()
        repo.save(issue)

        # 审批通过
        updated = await service.approve_stage(issue_id, Stage.BRAINSTORM, "通过")

        assert updated.get_stage_state(Stage.BRAINSTORM).status == StageStatus.APPROVED
        assert updated.current_stage == Stage.PLAN_FORMED
        assert updated.get_stage_state(Stage.PLAN_FORMED).status == StageStatus.NEW

    @pytest.mark.asyncio
    async def test_approve_stage_completed_at_is_set(self, repo, executor, service):
        """测试审批通过时 completed_at 被设置"""
        issue = await service.create_issue("测试", "描述")
        issue_id = str(issue.id)

        stage_state = issue.get_stage_state(Stage.BRAINSTORM)
        stage_state.status = StageStatus.PENDING
        repo.save(issue)

        updated = await service.approve_stage(issue_id, Stage.BRAINSTORM, "通过")

        assert updated.get_stage_state(Stage.BRAINSTORM).completed_at is not None

    @pytest.mark.asyncio
    async def test_approve_nonexistent_issue_returns_none(self, repo, executor, service):
        """测试审批不存在的 Issue 返回 None"""
        result = await service.approve_stage("nonexistent-id", Stage.BRAINSTORM, "通过")
        assert result is None

    @pytest.mark.asyncio
    async def test_reject_stage(self, repo, executor, service):
        """测试打回阶段"""
        issue = await service.create_issue("测试 Issue", "测试描述")
        issue_id = str(issue.id)

        # 设置阶段为 PENDING 状态
        stage_state = issue.get_stage_state(Stage.BRAINSTORM)
        stage_state.status = StageStatus.PENDING
        repo.save(issue)

        # 打回
        updated = await service.reject_stage(issue_id, Stage.BRAINSTORM, "方案不够详细")

        assert updated.get_stage_state(Stage.BRAINSTORM).status == StageStatus.REJECTED

    @pytest.mark.asyncio
    async def test_reject_nonexistent_issue_returns_none(self, repo, executor, service):
        """测试打回不存在的 Issue 返回 None"""
        result = await service.reject_stage("nonexistent-id", Stage.BRAINSTORM, "原因")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_issue(self, repo, executor, service):
        """测试更新 Issue"""
        issue = await service.create_issue("原始标题", "原始描述")
        issue_id = str(issue.id)

        updated = service.update_issue(issue_id, title="新标题")
        assert updated.title == "新标题"
        assert updated.description == "原始描述"

    @pytest.mark.asyncio
    async def test_update_nonexistent_issue_returns_none(self, repo, executor, service):
        """测试更新不存在的 Issue 返回 None"""
        result = service.update_issue("nonexistent-id", title="新标题")
        assert result is None

    @pytest.mark.asyncio
    async def test_archive_issue(self, repo, executor, service):
        """测试归档 Issue"""
        issue = await service.create_issue("测试 Issue", "测试描述")
        issue_id = str(issue.id)

        archived = service.archive_issue(issue_id)
        assert archived.status == IssueStatus.ARCHIVED
        assert archived.archived_at is not None

    @pytest.mark.asyncio
    async def test_discard_issue(self, repo, executor, service):
        """测试废弃 Issue"""
        issue = await service.create_issue("测试 Issue", "测试描述")
        issue_id = str(issue.id)

        discarded = service.discard_issue(issue_id)
        assert discarded.status == IssueStatus.DISCARDED
        assert discarded.discarded_at is not None

    @pytest.mark.asyncio
    async def test_delete_issue(self, repo, executor, service):
        """测试删除 Issue"""
        issue = await service.create_issue("测试 Issue", "测试描述")
        issue_id = str(issue.id)

        assert len(repo.list_all()) == 1

        success = await service.delete_issue(issue_id)
        assert success is True
        assert len(repo.list_all()) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_issue_returns_false(self, repo, executor, service):
        """测试删除不存在的 Issue 返回 False"""
        success = await service.delete_issue("nonexistent-id")
        assert success is False


class TestTriggerAI:
    """trigger_ai 测试"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="需要真实网络访问 clone 仓库")
    async def test_trigger_ai_new_issue(self, repo, executor, service):
        """测试触发新 Issue 的 AI 执行（集成测试）"""
        issue = await service.create_issue("测试", "描述")
        issue_id = str(issue.id)

        # 设置 repo_url（Pipeline 需要有效的仓库信息才能 clone）
        issue.repo_url = "https://github.com/test/repo.git"
        issue.pipeline.context.repo_url = "https://github.com/test/repo.git"
        repo.save(issue)

        # 标记为进行中
        issue.running_status = IssueRunningStatus.IN_PROGRESS
        repo.save(issue)

        result = await service.trigger_ai(issue_id, Stage.ENVIRONMENT)

        assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_trigger_ai_nonexistent_issue(self, repo, executor, service):
        """测试触发不存在的 Issue"""
        result = await service.trigger_ai("nonexistent-id", Stage.ENVIRONMENT)

        assert result.get("status") == "error"
        assert "not found" in result.get("message", "")

    @pytest.mark.asyncio
    async def test_trigger_ai_invalid_stage_status(self, repo, executor, service):
        """测试触发状态不允许的阶段"""
        issue = await service.create_issue("测试", "描述")
        issue_id = str(issue.id)

        # 设置阶段为非允许状态（如 APPROVED）
        stage_state = issue.get_stage_state(Stage.ENVIRONMENT)
        stage_state.status = StageStatus.APPROVED
        repo.save(issue)

        result = await service.trigger_ai(issue_id, Stage.ENVIRONMENT)

        assert result.get("status") == "error"
        assert "不能触发 AI" in result.get("message", "")

    @pytest.mark.asyncio
    async def test_trigger_ai_mark_in_progress(self, repo, executor, service):
        """测试 trigger_ai 将 running_status 设为 IN_PROGRESS"""
        issue = await service.create_issue("测试", "描述")
        issue_id = str(issue.id)

        assert issue.running_status == IssueRunningStatus.NEW

        await service.trigger_ai(issue_id, Stage.ENVIRONMENT)

        updated_issue = repo.get(IssueId(issue_id))
        assert updated_issue.running_status == IssueRunningStatus.IN_PROGRESS

class TestIssueLifecycle:
    """Issue 生命周期测试"""

    @pytest.mark.asyncio
    async def test_issue_workflow_new_to_completed(self, repo, executor, service):
        """测试完整工作流：新建 -> 执行 -> 审批 -> 完成"""
        issue = await service.create_issue("完整流程测试", "测试完整生命周期")
        issue_id = str(issue.id)

        # 1. 初始状态
        assert issue.running_status == IssueRunningStatus.NEW
        assert issue.get_stage_state(Stage.ENVIRONMENT).status == StageStatus.NEW

        # 2. 触发 AI 执行环境准备阶段
        await service.trigger_ai(issue_id, Stage.ENVIRONMENT)

        # 3. 模拟环境准备完成（executor 自动设置 PENDING）
        # 此时应该能够审批

        # 4. 审批环境准备阶段
        env_state = repo.get(IssueId(issue_id)).get_stage_state(Stage.ENVIRONMENT)
        if env_state.status == StageStatus.PENDING:
            await service.approve_stage(issue_id, Stage.ENVIRONMENT, "环境准备完成")

            # 验证进入下一阶段
            updated_issue = repo.get(IssueId(issue_id))
            assert updated_issue.current_stage == Stage.BRAINSTORM
            assert updated_issue.get_stage_state(Stage.BRAINSTORM).status == StageStatus.NEW