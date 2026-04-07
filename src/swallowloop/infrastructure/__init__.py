"""基础设施层 - 技术实现"""

MODULE_NAME = "infrastructure"

# 持久化
from .persistence import (
    InMemoryIssueRepository,
)

# Agent
from .agent import BaseAgent, AgentResult

# 配置
from .config import Config

# LLM
from .llm import LLMConfig, LLMProviderEnum

# 日志
from .logger import setup_logging, get_logger

# 实例注册
from .instance_registry import InstanceRegistry, get_instance, register_instance, clear_instances

__all__ = [
    "MODULE_NAME",
    # 持久化
    "InMemoryIssueRepository",
    # Agent
    "BaseAgent",
    "AgentResult",
    # 配置
    "Config",
    # LLM
    "LLMConfig",
    "LLMProviderEnum",
    # 日志
    "setup_logging",
    "get_logger",
    # 实例注册
    "InstanceRegistry",
    "get_instance",
    "register_instance",
    "clear_instances",
]
