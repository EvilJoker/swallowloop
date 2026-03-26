"""Agent 模块"""

MODULE_NAME = "infrastructure.agent"

from .base import BaseAgent, AgentResult
from .mock_agent import MockAgent

__all__ = ["MODULE_NAME", "BaseAgent", "AgentResult", "MockAgent"]
