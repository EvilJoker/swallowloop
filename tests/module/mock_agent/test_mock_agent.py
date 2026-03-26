"""MockAgent 模块测试"""

import pytest
import asyncio
import time

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
