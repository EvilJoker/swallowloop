"""MockAgent 模块测试"""

import pytest
import asyncio
import time
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

        workspace_info = await agent.prepare(
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
        assert "workspace" in workspace_info.workspace_path
        assert workspace_info.workspace_path.endswith("test-issue-123/workspace")

    @pytest.mark.asyncio
    async def test_mock_agent_prepare_workspace_created(self):
        """测试 MockAgent.prepare 创建工作空间目录"""
        agent = MockAgent(delay_seconds=0.01)
        await agent.initialize()

        workspace_info = await agent.prepare(
            issue_id="test-issue-workspace",
            context={"repo_url": "", "branch": "", "stage": ""}
        )

        # 验证工作空间目录已创建
        workspace_path = Path(workspace_info.workspace_path)
        assert workspace_path.exists()
        assert workspace_path.is_dir()
