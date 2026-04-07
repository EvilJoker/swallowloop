"""Agent 模块"""

MODULE_NAME = "infrastructure.agent"

import logging

from .base import AgentResult, AgentStatus, BaseAgent
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


def create_agent(agent_type: str = "deerflow") -> BaseAgent:
    """工厂函数：根据配置创建 Agent 实例"""
    config = _get_config()

    if agent_type == "deerflow":
        base_url = config.get("DEERFLOW_BASE_URL", DEFAULT_DEERFLOW_BASE_URL) if config else DEFAULT_DEERFLOW_BASE_URL
        logger.info(f"使用 DeerFlowAgent，base_url={base_url}")
        return DeerFlowAgent(base_url=base_url)
    else:
        raise ValueError(f"不支持的 Agent 类型: {agent_type}")


__all__ = [
    "MODULE_NAME",
    "AgentResult",
    "AgentStatus",
    "BaseAgent",
    "DeerFlowAgent",
    "create_agent",
]
