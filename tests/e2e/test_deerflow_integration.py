"""DeerFlow E2E 测试 - 验证 SwallowLoop 与 DeerFlow 的完整集成"""

import asyncio
import json
import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from swallowloop.application.service.issue_service import IssueService
from swallowloop.application.service.executor_service import ExecutorService
from swallowloop.domain.model import Issue, IssueId, Stage, StageStatus
from swallowloop.domain.repository import IssueRepository
from swallowloop.infrastructure.agent import DeerFlowAgent, Workspace


class MockIssueRepository(IssueRepository):
    """内存 Issue 仓库（测试用）"""

    def __init__(self):
        self._issues: dict[str, Issue] = {}

    def save(self, issue: Issue) -> None:
        self._issues[str(issue.id)] = issue

    def get(self, issue_id: IssueId) -> Issue | None:
        return self._issues.get(str(issue_id))

    def delete(self, issue_id: IssueId) -> bool:
        return self._issues.pop(str(issue_id), None) is not None

    def list_all(self) -> list[Issue]:
        return list(self._issues.values())

    def list_active(self) -> list[Issue]:
        return [i for i in self._issues.values() if i.status.value == "active"]

    def list_stages_by_status(self, stage: Stage, status: StageStatus) -> list[Issue]:
        return [
            i for i in self._issues.values()
            if i.stages[stage].status == status
        ]


class MockWebSocketManager:
    """Mock WebSocket Manager"""
    async def broadcast_issue(self, data: dict):
        pass


class TestDeerFlowAgentIntegration:
    """DeerFlow Agent 集成测试"""

    @pytest.fixture
    def mock_deerflow_agent(self):
        """创建 Mock DeerFlowAgent"""
        agent = MagicMock(spec=DeerFlowAgent)
        agent.prepare = MagicMock(return_value=Workspace(
            id="test-thread-123",
            ready=True,
            workspace_path="/tmp/test-workspace",
            repo_url="https://github.com/test/repo",
            branch="test-issue",
            metadata={}
        ))
        agent.execute = AsyncMock(return_value=MagicMock(
            success=True,
            output="Test execution completed",
            error=None
        ))
        return agent

    @pytest.fixture
    def mock_deerflow_client(self):
        """Mock httpx client for DeerFlow API（同步）"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "thread_id": "test-thread-123",
            "run_id": "test-run-456"
        }

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)
        return mock_client

    @pytest.mark.asyncio
    async def test_issue_create_and_trigger(self, mock_deerflow_agent):
        """测试创建 Issue 并触发 AI 执行"""
        # 1. 创建仓库和服务
        repo = MockIssueRepository()
        ws_manager = MockWebSocketManager()

        executor = ExecutorService(
            repository=repo,
            agent=mock_deerflow_agent,
            agent_type="deerflow",
            ws_manager=ws_manager
        )

        issue_service = IssueService(
            repository=repo,
            executor=executor,
            agent=mock_deerflow_agent,
            ws_manager=ws_manager
        )

        # 2. 创建 Issue
        issue = await issue_service.create_issue(
            title="Test Issue",
            description="Test description"
        )
        assert issue is not None
        assert issue.title == "Test Issue"
        assert issue.current_stage == Stage.ENVIRONMENT

        # 设置有效的 repo_url（Pipeline context 需要这个来 clone）
        issue.repo_url = "https://github.com/test/repo.git"
        issue.pipeline.set_context_value("repo_url", "https://github.com/test/repo.git")
        repo.save(issue)

        # 3. 触发 AI
        # 先触发 ENVIRONMENT 阶段（当前阶段）
        result = await issue_service.trigger_ai(str(issue.id), Stage.ENVIRONMENT)

        # 验证 trigger 返回成功
        assert result.get("success") is True or result.get("output") == ""

        # 4. 验证 workspace 已创建
        issue = repo.get(IssueId(str(issue.id)))
        assert issue.workspace is not None
        assert issue.thread_id == "test-thread-123"

    @pytest.mark.asyncio
    async def test_deerflow_agent_prepare(self, mock_deerflow_client):
        """测试 DeerFlowAgent.prepare() 创建 Thread"""
        agent = DeerFlowAgent(base_url="http://localhost:2026")

        with patch.object(agent, '_create_client', return_value=mock_deerflow_client):
            workspace = agent.prepare(
                issue_id="issue-456",
                context={
                    "repo_url": "https://github.com/test/repo",
                    "branch": "issue-456",
                    "stage": "prepare"
                }
            )

            assert workspace.id == "test-thread-123"
            assert workspace.ready is True
            assert ".deer-flow/threads/test-thread-123" in workspace.workspace_path
