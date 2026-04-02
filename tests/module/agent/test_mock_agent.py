"""MockAgent 模块测试"""

import pytest
import asyncio
import time
from datetime import datetime
from pathlib import Path

from swallowloop.infrastructure.agent import MockAgent


class TestMockAgent:
    """MockAgent 功能测试"""

    @pytest.mark.asyncio
    async def test_mock_agent_execute(self):
        """测试 MockAgent 执行"""
        agent = MockAgent(delay_seconds=0.01)
        await agent.initialize()
        result = await agent.execute(
            task="测试任务",
            context={"issue_id": "test-1", "stage": "brainstorm"}
        )

        assert result.success is True
        assert result.output is not None

    @pytest.mark.asyncio
    async def test_mock_agent_delay(self):
        """测试 MockAgent 延迟"""
        agent = MockAgent(delay_seconds=0.1)
        await agent.initialize()

        start = time.time()
        await agent.execute(task="测试任务", context={})
        elapsed = time.time() - start

        assert elapsed >= 0.1

    @pytest.mark.asyncio
    async def test_mock_agent_default_delay(self):
        """测试 MockAgent 默认延迟(5秒)"""
        agent = MockAgent()
        await agent.initialize()

        start = time.time()
        await agent.execute(task="测试任务", context={})
        elapsed = time.time() - start

        # 默认延迟 5 秒
        assert elapsed >= 5.0
        assert elapsed < 6.0

    @pytest.mark.asyncio
    async def test_mock_agent_prepare(self):
        """测试 MockAgent.prepare 准备工作空间"""
        agent = MockAgent(delay_seconds=0.01)
        await agent.initialize()

        workspace_info = agent.prepare(
            issue_id="test-issue-123",
            context={
                "repo_url": "https://github.com/test/repo",
                "branch": "test-issue-123",
                "stage": "brainstorm"
            }
        )

        # MockAgent 直接就绪
        assert workspace_info.ready is True
        assert workspace_info.id == "test-issue-123"
        assert workspace_info.repo_url == "https://github.com/test/repo"
        assert workspace_info.branch == "test-issue-123"
        assert workspace_info.workspace_path.endswith("test-issue-123")

    @pytest.mark.asyncio
    async def test_mock_agent_prepare_workspace_created(self):
        """测试 MockAgent.prepare 创建工作空间目录"""
        agent = MockAgent(delay_seconds=0.01)
        await agent.initialize()

        workspace_info = agent.prepare(
            issue_id="test-issue-workspace",
            context={"repo_url": "", "branch": "", "stage": ""}
        )

        # 验证工作空间目录已创建
        workspace_path = Path(workspace_info.workspace_path)
        assert workspace_path.exists()
        assert workspace_path.is_dir()


class TestMockAgentStatus:
    """MockAgent 状态方法测试"""

    def test_get_status_returns_cached_status(self):
        """测试 get_status 返回缓存状态"""
        agent = MockAgent(delay_seconds=0.01)
        status = agent.get_status()

        assert status.status == "online"
        assert status.version == "mock-1.0.0"
        assert status.model_name == "mock-model"
        assert status.model_display_name == "Mock Model"
        assert status.llm_used == 0
        assert status.llm_quota == 1500
        assert status.llm_next_refresh is None
        assert status.base_url == "mock://localhost"
        assert status.active_threads == 0
        assert status.last_update is not None

    @pytest.mark.asyncio
    async def test_fetch_status_returns_same_as_get_status(self):
        """测试 fetch_status 返回与 get_status 相同的缓存状态"""
        agent = MockAgent(delay_seconds=0.01)
        await agent.initialize()

        fetched_status = await agent.fetch_status()
        cached_status = agent.get_status()

        assert fetched_status.status == cached_status.status
        assert fetched_status.version == cached_status.version
        assert fetched_status.model_name == cached_status.model_name
        assert fetched_status.llm_used == cached_status.llm_used
        assert fetched_status.llm_quota == cached_status.llm_quota
        assert fetched_status.base_url == cached_status.base_url
