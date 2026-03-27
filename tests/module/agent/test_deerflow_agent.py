"""DeerFlowAgent 模块测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from swallowloop.infrastructure.agent import DeerFlowAgent, Workspace


class TestDeerFlowAgent:
    """DeerFlowAgent 功能测试"""

    @pytest.mark.asyncio
    async def test_deerflow_agent_prepare_creates_thread(self):
        """测试 DeerFlowAgent.prepare 创建 Thread"""
        agent = DeerFlowAgent(base_url="http://localhost:2026")

        # Mock httpx.AsyncClient
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"thread_id": "issue-123"}

        with patch.object(agent._client, 'post', new_callable=AsyncMock) as mock_post:
            with patch.object(agent._client, 'aclose', new_callable=AsyncMock):
                mock_post.return_value = mock_response

                workspace_info = await agent.prepare(
                    issue_id="issue-123",
                    context={
                        "repo_url": "https://github.com/test/repo",
                        "branch": "issue-123",
                        "stage": "brainstorm"
                    }
                )

                # 验证返回的 WorkspaceInfo
                assert workspace_info.id == "issue-123"
                assert workspace_info.ready is True
                assert workspace_info.repo_url == "https://github.com/test/repo"
                assert workspace_info.branch == "issue-123"
                assert ".deer-flow/threads/issue-123" in workspace_info.workspace_path

                # 验证调用了创建 Thread 的 API
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                assert "/api/langgraph/threads" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_deerflow_agent_prepare_uses_existing_thread_id(self):
        """测试 DeerFlowAgent.prepare 使用返回的 thread_id"""
        agent = DeerFlowAgent(base_url="http://localhost:2026")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"thread_id": "different-thread-id"}

        with patch.object(agent._client, 'post', new_callable=AsyncMock) as mock_post:
            with patch.object(agent._client, 'aclose', new_callable=AsyncMock):
                mock_post.return_value = mock_response

                workspace_info = await agent.prepare(
                    issue_id="issue-123",
                    context={"repo_url": "", "branch": "", "stage": ""}
                )

                # 使用返回的 thread_id
                assert workspace_info.id == "different-thread-id"

    @pytest.mark.asyncio
    async def test_deerflow_agent_execute_success(self):
        """测试 DeerFlowAgent.execute 成功执行"""
        agent = DeerFlowAgent(base_url="http://localhost:2026")

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(agent._client, 'post', new_callable=AsyncMock) as mock_post:
            with patch.object(agent._client, 'aclose', new_callable=AsyncMock):
                mock_post.return_value = mock_response

                result = await agent.execute(
                    task="分析这个代码",
                    context={
                        "thread_id": "issue-123",
                        "workspace_path": "/path/to/workspace"
                    }
                )

                assert result.success is True
                assert "DeerFlow" in result.output

    @pytest.mark.asyncio
    async def test_deerflow_agent_execute_missing_thread_id(self):
        """测试 DeerFlowAgent.execute 缺少 thread_id"""
        agent = DeerFlowAgent(base_url="http://localhost:2026")

        result = await agent.execute(
            task="分析这个代码",
            context={}  # 没有 thread_id
        )

        assert result.success is False
        assert "thread_id required" in result.error

    @pytest.mark.asyncio
    async def test_deerflow_agent_execute_error_response(self):
        """测试 DeerFlowAgent.execute 错误响应"""
        agent = DeerFlowAgent(base_url="http://localhost:2026")

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch.object(agent._client, 'post', new_callable=AsyncMock) as mock_post:
            with patch.object(agent._client, 'aclose', new_callable=AsyncMock):
                mock_post.return_value = mock_response

                result = await agent.execute(
                    task="分析这个代码",
                    context={"thread_id": "issue-123"}
                )

                assert result.success is False
                assert "500" in result.error

    @pytest.mark.asyncio
    async def test_deerflow_agent_cleanup(self):
        """测试 DeerFlowAgent.cleanup 清理 Thread"""
        agent = DeerFlowAgent(base_url="http://localhost:2026")

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(agent._client, 'delete', new_callable=AsyncMock) as mock_delete:
            with patch.object(agent._client, 'aclose', new_callable=AsyncMock):
                mock_delete.return_value = mock_response

                await agent.cleanup("issue-123")

                mock_delete.assert_called_once_with("http://localhost:2026/api/langgraph/threads/issue-123")

    @pytest.mark.asyncio
    async def test_deerflow_agent_workspace_path_format(self):
        """测试 DeerFlowAgent 返回正确的工作空间路径格式"""
        agent = DeerFlowAgent(base_url="http://localhost:2026")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"thread_id": "test-thread"}

        with patch.object(agent._client, 'post', new_callable=AsyncMock) as mock_post:
            with patch.object(agent._client, 'aclose', new_callable=AsyncMock):
                mock_post.return_value = mock_response

                workspace_info = await agent.prepare(
                    issue_id="test-thread",
                    context={"repo_url": "", "branch": "", "stage": ""}
                )

                # 验证路径格式
                assert workspace_info.workspace_path.endswith("test-thread/user-data/workspace")


class TestWorkspace:
    """Workspace 数据类测试"""

    def test_workspace_creation(self):
        """测试 Workspace 创建"""
        ws = Workspace(
            id="issue-123",
            ready=True,
            workspace_path="/path/to/workspace",
            repo_url="https://github.com/test/repo",
            branch="issue-123",
            metadata={"key": "value"}
        )

        assert ws.id == "issue-123"
        assert ws.ready is True
        assert ws.workspace_path == "/path/to/workspace"
        assert ws.repo_url == "https://github.com/test/repo"
        assert ws.branch == "issue-123"
        assert ws.metadata == {"key": "value"}

    def test_workspace_default_metadata(self):
        """测试 Workspace 默认 metadata"""
        ws = Workspace(
            id="issue-123",
            ready=False,
            workspace_path="/path",
            repo_url="",
            branch=""
        )

        assert ws.metadata == {}
