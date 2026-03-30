"""DeerFlowAgent 模块测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from swallowloop.infrastructure.agent import DeerFlowAgent, Workspace


class TestDeerFlowAgent:
    """DeerFlowAgent 功能测试"""

    def _create_mock_client(self, response_status: int = 200, response_json: dict = None):
        """创建 mock httpx.AsyncClient"""
        mock_response = MagicMock()
        mock_response.status_code = response_status
        if response_json:
            mock_response.json.return_value = response_json

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.delete = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        return mock_client

    @pytest.mark.asyncio
    async def test_deerflow_agent_prepare_creates_thread(self):
        """测试 DeerFlowAgent.prepare 创建 Thread"""
        agent = DeerFlowAgent(base_url="http://localhost:2024")
        mock_client = self._create_mock_client(
            response_status=200,
            response_json={"thread_id": "issue-123"}
        )

        with patch.object(agent, '_create_client', return_value=mock_client):
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

    @pytest.mark.asyncio
    async def test_deerflow_agent_prepare_uses_existing_thread_id(self):
        """测试 DeerFlowAgent.prepare 使用返回的 thread_id"""
        agent = DeerFlowAgent(base_url="http://localhost:2024")
        mock_client = self._create_mock_client(
            response_status=200,
            response_json={"thread_id": "different-thread-id"}
        )

        with patch.object(agent, '_create_client', return_value=mock_client):
            workspace_info = await agent.prepare(
                issue_id="issue-123",
                context={"repo_url": "", "branch": "", "stage": ""}
            )

            # 使用返回的 thread_id
            assert workspace_info.id == "different-thread-id"

    @pytest.mark.asyncio
    async def test_deerflow_agent_execute_success(self):
        """测试 DeerFlowAgent.execute 成功执行并提取响应"""
        agent = DeerFlowAgent(base_url="http://localhost:2024")

        # Mock run 提交响应
        mock_run_response = MagicMock()
        mock_run_response.status_code = 200
        mock_run_response.json.return_value = {"run_id": "run-123", "status": "pending"}

        # Mock thread 状态响应（包含消息）
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {
            "status": "success",
            "values": {
                "messages": [
                    {"type": "human", "content": "test task"},
                    {"type": "ai", "content": "AI response content"}
                ]
            }
        }

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_run_response)
        # 模拟轮询：一直返回 success 直到循环退出
        mock_client.get = AsyncMock(return_value=mock_success_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # 直接 patch _wait_for_run 方法来简化测试
        async def mock_wait_for_run(client, thread_id, run_id):
            return {
                "values": {
                    "messages": [
                        {"type": "human", "content": "test task"},
                        {"type": "ai", "content": "AI response content"}
                    ]
                }
            }

        with patch.object(agent, '_create_client', return_value=mock_client):
            with patch.object(agent, '_wait_for_run', mock_wait_for_run):
                result = await agent.execute(
                    task="分析这个代码",
                    context={
                        "thread_id": "issue-123",
                        "workspace_path": "/path/to/workspace"
                    }
                )

                assert result.success is True
                assert "AI response content" in result.output

    @pytest.mark.asyncio
    async def test_deerflow_agent_execute_missing_thread_id(self):
        """测试 DeerFlowAgent.execute 缺少 thread_id"""
        agent = DeerFlowAgent(base_url="http://localhost:2024")

        result = await agent.execute(
            task="分析这个代码",
            context={}  # 没有 thread_id
        )

        assert result.success is False
        assert "thread_id required" in result.error

    @pytest.mark.asyncio
    async def test_deerflow_agent_execute_error_response(self):
        """测试 DeerFlowAgent.execute 错误响应"""
        agent = DeerFlowAgent(base_url="http://localhost:2024")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch.object(agent, '_create_client', return_value=mock_client):
            result = await agent.execute(
                task="分析这个代码",
                context={"thread_id": "issue-123"}
            )

            assert result.success is False
            assert "500" in result.error

    @pytest.mark.asyncio
    async def test_deerflow_agent_cleanup(self):
        """测试 DeerFlowAgent.cleanup 清理 Thread"""
        agent = DeerFlowAgent(base_url="http://localhost:2024")

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = MagicMock()
        mock_client.delete = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch.object(agent, '_create_client', return_value=mock_client):
            await agent.cleanup("issue-123")

            mock_client.delete.assert_called_once_with("http://localhost:2024/threads/issue-123")

    @pytest.mark.asyncio
    async def test_deerflow_agent_workspace_path_format(self):
        """测试 DeerFlowAgent 返回正确的工作空间路径格式"""
        agent = DeerFlowAgent(base_url="http://localhost:2024")
        mock_client = self._create_mock_client(
            response_status=200,
            response_json={"thread_id": "test-thread"}
        )

        with patch.object(agent, '_create_client', return_value=mock_client):
            workspace_info = await agent.prepare(
                issue_id="test-thread",
                context={"repo_url": "", "branch": "", "stage": ""}
            )

            # 验证路径格式
            assert workspace_info.workspace_path.endswith("test-thread/user-data/workspace")

    @pytest.mark.asyncio
    async def test_deerflow_agent_extracts_tool_message_content(self):
        """测试 DeerFlowAgent 从 type=tool 消息中提取内容"""
        agent = DeerFlowAgent(base_url="http://localhost:2024")

        # 直接 patch _wait_for_run 方法来简化测试
        async def mock_wait_for_run(client, thread_id, run_id):
            return {
                "values": {
                    "messages": [
                        {"type": "human", "content": "task"},
                        {"type": "tool", "content": "This is tool response content"}
                    ]
                }
            }

        # Mock run 提交响应
        mock_run_response = MagicMock()
        mock_run_response.status_code = 200
        mock_run_response.json.return_value = {"run_id": "run-123", "status": "pending"}

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_run_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch.object(agent, '_create_client', return_value=mock_client):
            with patch.object(agent, '_wait_for_run', mock_wait_for_run):
                result = await agent.execute(
                    task="test",
                    context={"thread_id": "issue-123"}
                )

                assert result.success is True
                assert "tool response content" in result.output


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
