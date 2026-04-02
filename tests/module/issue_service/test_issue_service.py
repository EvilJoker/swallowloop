"""IssueService 模块测试"""

import pytest
import logging
from datetime import datetime
from swallowloop.domain.model import Stage, StageStatus, IssueStatus
from swallowloop.application.service import IssueService
from tests.helpers import MockRepository, MockExecutor

logger = logging.getLogger(__name__)


@pytest.fixture
def repo():
    return MockRepository()


@pytest.fixture
def executor(repo):
    return MockExecutor(repository=repo)


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
    async def test_update_issue(self, repo, executor, service):
        """测试更新 Issue"""
        issue = await service.create_issue("原始标题", "原始描述")
        issue_id = str(issue.id)

        updated = service.update_issue(issue_id, title="新标题")
        assert updated.title == "新标题"
        assert updated.description == "原始描述"

    @pytest.mark.asyncio
    async def test_archive_issue(self, repo, executor, service):
        """测试归档 Issue"""
        issue = await service.create_issue("测试 Issue", "测试描述")
        issue_id = str(issue.id)

        archived = service.archive_issue(issue_id)
        assert archived.status == IssueStatus.ARCHIVED
        assert archived.archived_at is not None

    @pytest.mark.asyncio
    async def test_delete_issue(self, repo, executor, service):
        """测试删除 Issue"""
        issue = await service.create_issue("测试 Issue", "测试描述")
        issue_id = str(issue.id)

        assert len(repo.list_all()) == 1

        success = await service.delete_issue(issue_id)
        assert success is True
        assert len(repo.list_all()) == 0