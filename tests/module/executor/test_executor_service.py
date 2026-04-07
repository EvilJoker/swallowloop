"""ExecutorService 错误场景测试"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from swallowloop.application.service.executor_service import ExecutorService
from swallowloop.domain.model import Issue, IssueId, Stage, StageStatus, IssueStatus
from swallowloop.domain.model.workspace import Workspace
from swallowloop.infrastructure.agent.base import AgentResult
from tests.helpers import MockRepository


@pytest.fixture
def repo():
    return MockRepository()


@pytest.fixture
def agent():
    """创建 Mock Agent"""
    mock_workspace = Workspace(
        id="thread-123",
        ready=True,
        workspace_path="/tmp/test-workspace",
        repo_url="https://github.com/test/repo",
        branch="test-branch"
    )
    agent = MagicMock()
    agent.prepare = MagicMock(return_value=mock_workspace)  # prepare 是同步方法
    agent.execute = AsyncMock(return_value=AgentResult(
        success=True, output="done", error=None
    ))
    return agent


@pytest.fixture
def executor(repo, agent):
    return ExecutorService(repository=repo, agent=agent, agent_type="mock")


class TestPrepareWorkspace:
    """prepare_workspace 错误场景测试"""

    @pytest.mark.asyncio
    async def test_prepare_workspace_success(self, repo, executor, agent):
        """测试成功创建 workspace"""
        issue = Issue(
            id=IssueId("test-issue"),
            title="测试",
            description="描述",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.ENVIRONMENT,
            created_at=datetime.now(),
        )
        repo.save(issue)

        result = await executor.prepare_workspace(issue, Stage.ENVIRONMENT)

        assert result is True
        assert issue.thread_id == "thread-123"
        assert agent.prepare.called

    @pytest.mark.asyncio
    async def test_prepare_workspace_agent_failure(self, repo, agent):
        """测试 agent.prepare 失败"""
        # 配置 agent.prepare 抛出异常（prepare 是同步方法，使用 MagicMock）
        agent.prepare = MagicMock(side_effect=Exception("DeerFlow 连接失败"))

        executor = ExecutorService(repository=repo, agent=agent, agent_type="deerflow")

        issue = Issue(
            id=IssueId("test-issue"),
            title="测试",
            description="描述",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.ENVIRONMENT,
            created_at=datetime.now(),
        )
        repo.save(issue)

        result = await executor.prepare_workspace(issue, Stage.ENVIRONMENT)

        assert result is False

    @pytest.mark.asyncio
    async def test_prepare_workspace_reuses_existing_thread(self, repo, executor, agent):
        """测试复用已有的 thread_id"""
        issue = Issue(
            id=IssueId("test-issue"),
            title="测试",
            description="描述",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.ENVIRONMENT,
            created_at=datetime.now(),
        )
        issue.thread_id = "existing-thread"
        issue.thread_path = "/tmp/existing-path"
        repo.save(issue)

        result = await executor.prepare_workspace(issue, Stage.ENVIRONMENT)

        assert result is True
        # 不应该再调用 agent.prepare
        agent.prepare.assert_not_called()


class TestExecuteStage:
    """execute_stage 错误场景测试"""

    @pytest.mark.asyncio
    async def test_execute_stage_without_thread_id(self, repo, executor, agent):
        """测试缺少 thread_id 时返回错误"""
        issue = Issue(
            id=IssueId("test-issue"),
            title="测试",
            description="描述",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        # 没有设置 thread_id
        repo.save(issue)

        result = await executor.execute_stage(issue, Stage.BRAINSTORM)

        assert result["success"] is False
        assert "thread_path not found" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_stage_success(self, repo, executor, agent):
        """测试成功执行阶段"""
        issue = Issue(
            id=IssueId("test-issue"),
            title="测试",
            description="描述",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        issue.thread_id = "thread-123"
        issue.thread_path = "/tmp/test-workspace"
        repo.save(issue)

        result = await executor.execute_stage(issue, Stage.BRAINSTORM)

        assert result["success"] is True
        assert agent.execute.called

    @pytest.mark.asyncio
    async def test_execute_stage_agent_failure(self, repo, agent):
        """测试 agent.execute 失败"""
        agent.execute = AsyncMock(return_value=AgentResult(
            success=False, output="", error="Agent 执行失败"
        ))

        executor = ExecutorService(repository=repo, agent=agent, agent_type="deerflow")

        issue = Issue(
            id=IssueId("test-issue"),
            title="测试",
            description="描述",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        issue.thread_id = "thread-123"
        issue.thread_path = "/tmp/test-workspace"
        repo.save(issue)

        result = await executor.execute_stage(issue, Stage.BRAINSTORM)

        assert result["success"] is False
        assert "Agent 执行失败" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_stage_updates_issue_status(self, repo, executor, agent):
        """测试执行后更新 Issue 状态"""
        issue = Issue(
            id=IssueId("test-issue"),
            title="测试",
            description="描述",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        issue.thread_id = "thread-123"
        issue.thread_path = "/tmp/test-workspace"
        repo.save(issue)

        await executor.execute_stage(issue, Stage.BRAINSTORM)

        updated = repo.get(IssueId("test-issue"))
        assert updated.get_stage_state(Stage.BRAINSTORM).status == StageStatus.PENDING
