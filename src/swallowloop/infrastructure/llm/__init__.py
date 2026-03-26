"""LLM 配置管理"""

MODULE_NAME = "infrastructure.llm"

from .config import LLMConfig, LLMProvider

__all__ = ["MODULE_NAME", "LLMConfig", "LLMProvider"]
