"""Agent 模块"""

MODULE_NAME = "infrastructure.agent"

from .base import BaseAgent, AgentResult
from .mock_agent import MockAgent
from .deerflow_agent import DeerFlowAgent
from ...domain.model.workspace import Workspace

__all__ = ["MODULE_NAME", "BaseAgent", "AgentResult", "Workspace", "MockAgent", "DeerFlowAgent"]
