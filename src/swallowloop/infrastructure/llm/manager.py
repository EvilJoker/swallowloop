"""LLM 全局管理 - 提供统一的 LLM 实例获取"""

import logging
from typing import Optional

from .LLMProviderBase import LLMProviderBase, LLMUsage
from .LLMProviderMinimax import LLMProviderMinimax

logger = logging.getLogger(__name__)


def get_llm_instance() -> Optional[LLMProviderBase]:
    """
    获取全局 LLM 实例（单例）

    Returns:
        LLMProviderBase 实例，或 None（未初始化）
    """
    try:
        return LLMProviderMinimax.get_instance()
    except RuntimeError:
        return None


def get_llm_usage() -> Optional[LLMUsage]:
    """
    获取全局 LLM 使用量（不发起请求）

    Returns:
        LLMUsage 或 None（如果未初始化）
    """
    instance = get_llm_instance()
    if instance is None:
        return None
    return instance.get_usage()


def init_llm() -> LLMProviderBase:
    """
    初始化 LLM 单例（从 Config 模块加载配置）

    Returns:
        LLMProviderBase 实例
    """
    return LLMProviderMinimax.set_instance()
