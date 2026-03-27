"""基础设施层 - 技术实现"""

MODULE_NAME = "infrastructure"

# 持久化
from .persistence import (
    InMemoryIssueRepository,
)

# Agent
from .agent import BaseAgent, MockAgent, AgentResult

# 配置
from .config import Settings

# LLM
from .llm import LLMConfig, LLMProvider

# 日志
from .logger import setup_logging, get_logger

# 自更新
from .self_update import SelfUpdater

# 实例注册
from .instance_registry import InstanceRegistry, get_instance, register_instance, clear_instances

__all__ = [
    "MODULE_NAME",
    # 持久化
    "InMemoryIssueRepository",
    # Agent
    "BaseAgent",
    "MockAgent",
    "AgentResult",
    # 配置
    "Settings",
    # LLM
    "LLMConfig",
    "LLMProvider",
    # 日志
    "setup_logging",
    "get_logger",
    # 自更新
    "SelfUpdater",
    # 实例注册
    "InstanceRegistry",
    "get_instance",
    "register_instance",
    "clear_instances",
]
