"""ExecutorService 错误场景测试"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from swallowloop.application.service.executor_service import ExecutorService
from swallowloop.domain.model import Issue, IssueId, Stage, StageStatus, IssueStatus
from swallowloop.domain.model.workspace import Workspace
from swallowloop.infrastructure.agent.base import AgentResult
from swallowloop.domain.pipeline.context import PipelineContext
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
    return ExecutorService(repository=repo, agent=agent, agent_type="deerflow")


class TestExecuteStage:
    """execute_stage 统一 Pipeline 执行测试"""

    @pytest.mark.asyncio
    async def test_execute_stage_brainstorm_success(self, repo, executor, agent):
        """测试成功执行 BRAINSTORM 阶段（通过 Pipeline）"""
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


class TestEnvironmentStageWorkspaceSync:
    """环境准备阶段 workspace 同步测试 - 防护 Issue #workspace null 问题"""

    @pytest.mark.asyncio
    async def test_environment_stage_syncs_workspace_to_issue(self, repo, executor, agent):
        """测试 ENVIRONMENT 阶段执行后 workspace 同步到 issue

        这是核心回归测试，验证 Pipeline 执行完后 workspace 信息正确同步到 issue。
        问题根因：之前 ExecutorService.execute_environment() 没有同步 workspace，
        导致 issue.workspace 为 null。
        """
        issue = Issue(
            id=IssueId("test-issue"),
            title="测试",
            description="描述",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.ENVIRONMENT,
            created_at=datetime.now(),
        )
        repo.save(issue)

        # Mock Pipeline.execute_environment() 返回成功结果
        mock_context = PipelineContext(
            issue_id="test-issue",
            workspace_path="/tmp/test-workspace",
            repo_url="https://github.com/test/repo",
            repo_name="repo",
            branch="test-issue",
        )
        mock_context.thread_id = "thread-123"

        with patch.object(issue.pipeline, 'execute_environment') as mock_exec:
            mock_exec.return_value = {
                "success": True,
                "message": "环境准备完成",
            }
            with patch.object(issue.pipeline, 'get_context') as mock_ctx:
                mock_ctx.return_value = mock_context

                result = await executor.execute_stage(issue, Stage.ENVIRONMENT)

        # 验证执行成功
        assert result["success"] is True

        # 验证 workspace 已同步到 issue
        updated = repo.get(IssueId("test-issue"))
        assert updated.workspace is not None, "workspace 不应为 null"
        assert updated.workspace.id == "thread-123"
        assert updated.workspace.workspace_path == "/tmp/test-workspace"
        assert updated.workspace.repo_url == "https://github.com/test/repo"
        assert updated.workspace.branch == "test-issue"

        # 验证 thread_path 和 thread_id 也已同步
        assert updated.thread_path == "/tmp/test-workspace"
        assert updated.thread_id == "thread-123"

    @pytest.mark.asyncio
    async def test_environment_stage_syncs_workspace_on_failure(self, repo, executor, agent):
        """测试 ENVIRONMENT 阶段失败时 workspace 也应该同步（部分成功场景）"""
        issue = Issue(
            id=IssueId("test-issue"),
            title="测试",
            description="描述",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.ENVIRONMENT,
            created_at=datetime.now(),
        )
        repo.save(issue)

        mock_context = PipelineContext(
            issue_id="test-issue",
            workspace_path="/tmp/test-workspace",
            repo_url="https://github.com/test/repo",
            repo_name="repo",
            branch="test-issue",
        )
        mock_context.thread_id = "thread-123"

        # 即使返回 success=False，只要 workspace_path 存在就应该同步
        with patch.object(issue.pipeline, 'execute_environment') as mock_exec:
            mock_exec.return_value = {
                "success": False,
                "message": "部分任务失败",
            }
            with patch.object(issue.pipeline, 'get_context') as mock_ctx:
                mock_ctx.return_value = mock_context

                result = await executor.execute_stage(issue, Stage.ENVIRONMENT)

        # 验证 workspace 已同步（即使整体失败）
        updated = repo.get(IssueId("test-issue"))
        assert updated.workspace is not None, "workspace 不应为 null"
        assert updated.thread_path == "/tmp/test-workspace"
        assert updated.thread_id == "thread-123"

    @pytest.mark.asyncio
    async def test_issue_service_trigger_ai_delegates_to_executor(self, repo, executor, agent):
        """测试 IssueService.trigger_ai() 委托给 ExecutorService 执行

        验证手动触发和自动触发（StageLoop）走同一条执行路径。
        """
        from swallowloop.application.service.issue_service import IssueService

        issue_service = IssueService(
            repository=repo,
            executor=executor,
            agent=agent,
        )

        issue = Issue(
            id=IssueId("test-issue"),
            title="测试",
            description="描述",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.ENVIRONMENT,
            created_at=datetime.now(),
        )
        repo.save(issue)

        mock_context = PipelineContext(
            issue_id="test-issue",
            workspace_path="/tmp/test-workspace",
            repo_url="https://github.com/test/repo",
            repo_name="repo",
            branch="test-issue",
        )
        mock_context.thread_id = "thread-123"

        with patch.object(issue.pipeline, 'execute_environment') as mock_exec:
            mock_exec.return_value = {"success": True, "message": "完成"}
            with patch.object(issue.pipeline, 'get_context') as mock_ctx:
                mock_ctx.return_value = mock_context

                result = await issue_service.trigger_ai("test-issue", Stage.ENVIRONMENT)

        assert result["success"] is True

        # 验证 workspace 正确同步（通过 IssueService -> ExecutorService 路径）
        updated = repo.get(IssueId("test-issue"))
        assert updated.workspace is not None
        assert updated.workspace.workspace_path == "/tmp/test-workspace"
