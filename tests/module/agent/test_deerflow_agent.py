"""DeerFlowAgent 模块测试"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

from swallowloop.infrastructure.agent import DeerFlowAgent, Workspace


class TestDeerFlowAgent:
    """DeerFlowAgent 功能测试"""

    def _create_mock_client(self, response_status: int = 200, response_json: dict = None):
        """创建 mock httpx.Client（同步）"""
        mock_response = MagicMock()
        mock_response.status_code = response_status
        if response_json:
            mock_response.json.return_value = response_json

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.get.return_value = mock_response
        mock_client.delete.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)
        return mock_client

    @pytest.mark.asyncio
    async def test_deerflow_agent_prepare_creates_thread(self):
        """测试 DeerFlowAgent.prepare 创建 Thread"""
        agent = DeerFlowAgent(base_url="http://localhost:2024")
        mock_client = self._create_mock_client(
            response_status=200,
            response_json={"thread_id": "new-thread-123"}
        )

        with patch.object(agent, '_create_client', return_value=mock_client):
            with patch.object(Path, 'mkdir'):
                workspace_info = agent.prepare(
                    issue_id="issue-123",
                    context={
                        "repo_url": "https://github.com/test/repo",
                        "branch": "issue-123",
                        "stage": "brainstorm"
                    }
                )

                # 验证返回的 WorkspaceInfo
                assert workspace_info.id == "new-thread-123"
                assert workspace_info.ready is True
                assert workspace_info.repo_url == "https://github.com/test/repo"
                assert workspace_info.branch == "issue-123"
                assert ".deer-flow/threads/new-thread-123" in workspace_info.workspace_path

    @pytest.mark.asyncio
    async def test_deerflow_agent_prepare_uses_existing_thread_id(self):
        """测试 DeerFlowAgent.prepare 使用返回的 thread_id"""
        agent = DeerFlowAgent(base_url="http://localhost:2024")
        mock_client = self._create_mock_client(
            response_status=200,
            response_json={"thread_id": "different-thread-id"}
        )

        with patch.object(agent, '_create_client', return_value=mock_client):
            with patch.object(Path, 'mkdir'):
                workspace_info = agent.prepare(
                    issue_id="issue-123",
                    context={"repo_url": "", "branch": "", "stage": ""}
                )

                # 使用返回的 thread_id
                assert workspace_info.id == "different-thread-id"

    @pytest.mark.asyncio
    async def test_deerflow_agent_execute_success(self):
        """测试 DeerFlowAgent.execute 成功执行并轮询 result.json"""
        agent = DeerFlowAgent(base_url="http://localhost:2024")

        # Mock run 提交响应
        mock_run_response = MagicMock()
        mock_run_response.status_code = 200
        mock_run_response.json.return_value = {"run_id": "run-123", "status": "pending"}

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_run_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Mock result.json 存在
        result_data = {
            "status": "success",
            "output": "Task completed successfully",
            "files": ["output.txt"],
            "error": ""
        }

        with patch.object(agent, '_create_async_client', return_value=mock_client):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', mock_open(read_data=json.dumps(result_data))):
                    result = await agent.execute(
                        task="请读取并执行任务",
                        context={
                            "thread_id": "issue-123",
                            "stage_file": "/path/to/stage.md",
                            "result_file": "/path/to/result.json"
                        }
                    )

                    assert result.success is True
                    assert "Task completed successfully" in result.output

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
    async def test_deerflow_agent_execute_missing_stage_files(self):
        """测试 DeerFlowAgent.execute 缺少 stage_file 或 result_file"""
        agent = DeerFlowAgent(base_url="http://localhost:2024")

        result = await agent.execute(
            task="分析这个代码",
            context={"thread_id": "issue-123"}  # 没有 stage_file 和 result_file
        )

        assert result.success is False
        assert "stage_file 和 result_file 必须提供" in result.error

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

        with patch.object(agent._cleanup_client, 'delete_thread', new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = True
            await agent.cleanup("issue-123")

            mock_delete.assert_called_once_with("issue-123")

    @pytest.mark.asyncio
    async def test_deerflow_agent_workspace_path_format(self):
        """测试 DeerFlowAgent 返回正确的工作空间路径格式"""
        agent = DeerFlowAgent(base_url="http://localhost:2024")
        mock_client = self._create_mock_client(
            response_status=200,
            response_json={"thread_id": "test-thread"}
        )

        with patch.object(agent, '_create_client', return_value=mock_client):
            with patch.object(Path, 'mkdir'):
                workspace_info = agent.prepare(
                    issue_id="test-thread",
                    context={"repo_url": "", "branch": "", "stage": ""}
                )

                # 验证路径格式: ~/.deer-flow/.deer-flow/threads/{thread_id}/user-data/workspace
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


class TestDeerFlowAgentStatus:
    """DeerFlowAgent 状态方法测试"""

    def test_get_status_returns_initial_offline_status(self):
        """测试 get_status 返回初始离线状态"""
        agent = DeerFlowAgent(base_url="http://localhost:2026")
        status = agent.get_status()

        assert status.status == "offline"
        assert status.version is None
        assert status.model_name is None
        assert status.model_display_name is None
        assert status.llm_used == 0
        assert status.llm_quota == 1500
        assert status.base_url == "http://localhost:2026"
        assert status.last_update is None

    @pytest.mark.asyncio
    async def test_fetch_status_updates_cache_online(self):
        """测试 fetch_status 刷新缓存为在线状态"""
        agent = DeerFlowAgent(base_url="http://localhost:2026")

        # Mock health check 返回在线
        mock_health_response = MagicMock()
        mock_health_response.status_code = 200
        mock_health_response.json.return_value = {"version": "0.7.65"}

        # Mock model 返回
        mock_model_response = MagicMock()
        mock_model_response.status_code = 200
        mock_model_response.json.return_value = {
            "models": [{"model": "MiniMax-M2.7-highspeed", "display_name": "MiniMax M2.7 Highspeed"}]
        }

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=[mock_health_response, mock_model_response])

        # Mock LLM instance
        mock_llm = MagicMock()
        mock_llm.fetch_usage = AsyncMock(return_value=MagicMock(
            used=100,
            quota=1500,
            next_refresh=None
        ))

        with patch.object(agent, '_create_client', return_value=mock_client):
            with patch('swallowloop.infrastructure.agent.deerflow_agent.get_llm_instance', return_value=mock_llm):
                status = await agent.fetch_status()

        assert status.status == "online"
        assert status.version == "0.7.65"
        assert status.model_name == "MiniMax-M2.7-highspeed"
        assert status.model_display_name == "MiniMax M2.7 Highspeed"
        assert status.llm_used == 100
        assert status.llm_quota == 1500
        assert status.base_url == "http://localhost:2026"
        assert status.last_update is not None

    @pytest.mark.asyncio
    async def test_fetch_status_updates_cache_offline(self):
        """测试 fetch_status 刷新缓存为离线状态"""
        agent = DeerFlowAgent(base_url="http://localhost:2026")

        # Mock httpx.AsyncClient 直接抛出异常
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(side_effect=Exception("Connection timeout"))
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client):
            with patch('swallowloop.infrastructure.agent.deerflow_agent.get_llm_instance', return_value=None):
                status = await agent.fetch_status()

        assert status.status == "offline"
        assert status.version is None
        assert status.model_name is None

    @pytest.mark.asyncio
    async def test_fetch_status_preserves_active_threads(self):
        """测试 fetch_status 保持 active_threads 不变"""
        agent = DeerFlowAgent(base_url="http://localhost:2026")
        agent._status.active_threads = 5  # 手动设置

        # Mock health check
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=[
            MagicMock(status_code=200, json=MagicMock(return_value={"version": "0.7.65"})),
            MagicMock(status_code=200, json=MagicMock(return_value={"models": []}))
        ])

        with patch.object(agent, '_create_client', return_value=mock_client):
            with patch('swallowloop.infrastructure.agent.deerflow_agent.get_llm_instance', return_value=None):
                status = await agent.fetch_status()

        # active_threads 应该保持不变
        assert status.active_threads == 5
