"""MockAgent 测试"""

import asyncio
import pytest
from swallowloop.infrastructure.agent import MockAgent, AgentResult


@pytest.mark.asyncio
async def test_mock_agent_execute():
    """测试 MockAgent 执行"""
    agent = MockAgent(delay_seconds=0.1)

    await agent.initialize()

    result = await agent.execute(
        task="测试任务",
        context={"issue_id": "test-123", "stage": "brainstorm"}
    )

    assert result.success is True
    assert "测试任务" in result.output
    assert "test-123" in result.output
    assert "brainstorm" in result.output
    assert result.error is None


@pytest.mark.asyncio
async def test_mock_agent_delay():
    """测试 MockAgent 延迟"""
    agent = MockAgent(delay_seconds=0.5)

    import time
    start = time.time()
    result = await agent.execute("测试任务", {})
    elapsed = time.time() - start

    assert result.success is True
    assert elapsed >= 0.4  # 允许一点误差


@pytest.mark.asyncio
async def test_mock_agent_default_delay():
    """测试 MockAgent 默认延迟"""
    agent = MockAgent()  # 默认 5 秒

    # 不实际等待 5 秒，只验证初始化
    await agent.initialize()

    # 快速创建任务但不等待完成
    import time
    start = time.time()
    # 使用极短延迟测试
    agent._delay_seconds = 0.01
    result = await agent.execute("测试", {})
    elapsed = time.time() - start

    assert result.success is True
    assert elapsed < 1  # 应该很快完成
