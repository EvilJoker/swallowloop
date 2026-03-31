"""Agent 模块"""

MODULE_NAME = "infrastructure.agent"

import logging
import os

from .base import BaseAgent, AgentResult
from .mock_agent import MockAgent
from .deerflow_agent import DeerFlowAgent
from ...domain.model.workspace import Workspace

logger = logging.getLogger(__name__)


def create_agent(agent_type: str = "mock") -> BaseAgent:
    """工厂函数：根据配置创建 Agent 实例"""
    if agent_type == "mock":
        logger.info("使用 MockAgent，延迟 5 秒")
        return MockAgent(delay_seconds=5.0)
    elif agent_type == "deerflow":
        base_url = os.getenv("DEERFLOW_BASE_URL", "http://localhost:2024")
        logger.info(f"使用 DeerFlowAgent，base_url={base_url}")
        return DeerFlowAgent(base_url=base_url)
    else:
        logger.warning(f"Agent 类型 '{agent_type}' 暂不支持，使用 MockAgent")
        return MockAgent(delay_seconds=5.0)


__all__ = [
    "MODULE_NAME",
    "BaseAgent",
    "AgentResult",
    "Workspace",
    "MockAgent",
    "DeerFlowAgent",
    "create_agent",
]
