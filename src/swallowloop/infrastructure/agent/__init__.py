"""Agent 模块"""

MODULE_NAME = "infrastructure.agent"

import logging

from .base import AgentResult, AgentStatus, BaseAgent
from .mock_agent import MockAgent
from .deerflow_agent import DeerFlowAgent
from ...domain.model.workspace import Workspace
from ..constants import DEFAULT_DEERFLOW_BASE_URL

logger = logging.getLogger(__name__)


def _get_config() -> "Config | None":
    """获取 Config 实例"""
    try:
        from ...infrastructure.config import Config
        return Config.get_instance()
    except Exception:
        return None


def create_agent(agent_type: str = "mock") -> BaseAgent:
    """工厂函数：根据配置创建 Agent 实例"""
    config = _get_config()

    if agent_type == "mock":
        logger.info("使用 MockAgent，延迟 5 秒")
        return MockAgent(delay_seconds=5.0)
    elif agent_type == "deerflow":
        base_url = config.get("DEERFLOW_BASE_URL", DEFAULT_DEERFLOW_BASE_URL) if config else DEFAULT_DEERFLOW_BASE_URL
        logger.info(f"使用 DeerFlowAgent，base_url={base_url}")
        return DeerFlowAgent(base_url=base_url)
    else:
        logger.warning(f"Agent 类型 '{agent_type}' 暂不支持，使用 MockAgent")
        return MockAgent(delay_seconds=5.0)


__all__ = [
    "MODULE_NAME",
    "AgentResult",
    "AgentStatus",
    "BaseAgent",
    "Workspace",
    "MockAgent",
    "DeerFlowAgent",
    "create_agent",
]
