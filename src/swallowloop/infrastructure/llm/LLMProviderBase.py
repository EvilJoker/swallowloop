"""LLM Provider 基类定义"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class LLMProviderEnum(Enum):
    """支持的 LLM 提供商"""
    OPENAI = "openai"
    MINIMAX = "minimax"
    CUSTOM = "custom"


@dataclass
class LLMUsage:
    """LLM 使用量信息"""
    used: int = 0
    quota: int = 0
    last_call: datetime | None = None
    next_refresh: datetime | None = None


@dataclass
class LLMConfig:
    """LLM 配置类"""
    provider: LLMProviderEnum
    model_name: str
    api_key: str | None = None
    base_url: str | None = None


class LLMProviderBase(ABC):
    """LLM 抽象基类（单例）"""

    @abstractmethod
    def get_config(self) -> LLMConfig:
        """返回 LLM 配置"""
        pass


    @abstractmethod
    def load_config(self) -> None:
        """从 Config 模块加载配置"""
        pass

    @abstractmethod
    def get_usage(self) -> LLMUsage:
        """获取当前 LLM 使用量（不发起请求）"""
        pass

    @abstractmethod
    async def fetch_usage(self) -> LLMUsage:
        """从远端获取 LLM 使用量并更新"""
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """初始化 LLM 连接"""
        pass


    @classmethod
    @abstractmethod
    def get_instance(cls) -> "LLMProviderBase":
        """获取单例实例"""
        pass
