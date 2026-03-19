"""LLM 配置定义"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LLMProvider(Enum):
    """支持的 LLM 提供商"""
    IDEFAULT = "iflow"  # 使用本地 iFlow 默认配置
    OPENAI = "openai"
    MINIMAX = "minimax"
    CUSTOM = "custom"


@dataclass
class LLMConfig:
    """
    LLM 配置类
    
    支持多种 LLM 提供商，提供统一的配置接口。
    Agent 可以从 LLMConfig 获取所需的认证信息。
    """
    
    # 提供商
    provider: LLMProvider = LLMProvider.IDEFAULT
    
    # 基础配置
    model_name: str = ""
    
    # API 配置（可选，某些提供商需要）
    api_key: str | None = None
    base_url: str | None = None
    
    # 额外参数
    extra_params: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后处理：根据 provider 设置默认值"""
        if self.provider == LLMProvider.MINIMAX:
            if not self.base_url:
                self.base_url = "https://api.minimaxi.com/v1"
            if not self.model_name:
                self.model_name = "m2.7"
        elif self.provider == LLMProvider.OPENAI:
            if not self.base_url:
                self.base_url = "https://api.openai.com/v1"
            if not self.model_name:
                self.model_name = "gpt-4o"
    
    @property
    def is_default(self) -> bool:
        """是否使用默认配置（不需要额外认证）"""
        return self.provider == LLMProvider.IDEFAULT
    
    def to_iflow_auth_info(self) -> dict[str, Any] | None:
        """
        转换为 iFlow SDK 需要的认证信息格式
        
        Returns:
            如果是默认配置，返回 None（使用本地 iFlow 配置）
            否则返回认证信息字典
        """
        if self.is_default:
            return None
        
        info = {}
        if self.api_key:
            info["apiKey"] = self.api_key
        if self.base_url:
            info["baseUrl"] = self.base_url
        if self.model_name:
            info["modelName"] = self.model_name
        
        return info if info else None
    
    @property
    def iflow_auth_method_id(self) -> str | None:
        """获取 iFlow 认证方式 ID"""
        if self.is_default:
            return None
        # iFlow 支持的认证方式：openai-compatible
        return "openai-compatible"
    
    @classmethod
    def from_env(cls, prefix: str = "LLM") -> "LLMConfig":
        """
        从环境变量加载配置
        
        Args:
            prefix: 环境变量前缀，默认 "LLM"
                   例如: LLM_PROVIDER, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_NAME
        
        Returns:
            LLMConfig 实例
        """
        import os
        
        # 读取提供商
        provider_str = os.getenv(f"{prefix}_PROVIDER", "iflow").lower()
        try:
            provider = LLMProvider(provider_str)
        except ValueError:
            provider = LLMProvider.CUSTOM
        
        # 读取其他配置
        api_key = os.getenv(f"{prefix}_API_KEY")
        base_url = os.getenv(f"{prefix}_BASE_URL")
        model_name = os.getenv(f"{prefix}_MODEL_NAME", "")
        
        return cls(
            provider=provider,
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
        )
    
    @classmethod
    def minimax(cls, api_key: str, model_name: str = "m2.7") -> "LLMConfig":
        """创建 Minimax 配置"""
        return cls(
            provider=LLMProvider.MINIMAX,
            model_name=model_name,
            api_key=api_key,
            base_url="https://api.minimaxi.com/v1",
        )
    
    @classmethod
    def openai(cls, api_key: str, model_name: str = "gpt-4o") -> "LLMConfig":
        """创建 OpenAI 配置"""
        return cls(
            provider=LLMProvider.OPENAI,
            model_name=model_name,
            api_key=api_key,
            base_url="https://api.openai.com/v1",
        )
    
    @classmethod
    def custom(cls, api_key: str, base_url: str, model_name: str) -> "LLMConfig":
        """创建自定义配置"""
        return cls(
            provider=LLMProvider.CUSTOM,
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
        )
    
    @classmethod
    def default(cls) -> "LLMConfig":
        """创建默认配置（使用本地 iFlow）"""
        return cls(provider=LLMProvider.IDEFAULT)
    
    def __repr__(self) -> str:
        """安全的字符串表示，隐藏敏感信息"""
        api_key_masked = None
        if self.api_key:
            api_key_masked = f"{self.api_key[:8]}...{self.api_key[-4:]}" if len(self.api_key) > 12 else "***"
        
        return (
            f"LLMConfig(provider={self.provider.value}, "
            f"model={self.model_name}, "
            f"base_url={self.base_url}, "
            f"api_key={api_key_masked})"
        )
