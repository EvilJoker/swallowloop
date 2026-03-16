"""LLM 提供商基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    model: str
    usage: dict[str, int] | None = None
    finish_reason: str | None = None


class LLMProvider(ABC):
    """
    LLM 提供商接口
    
    定义大语言模型调用的抽象操作
    """
    
    @abstractmethod
    def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs
    ) -> LLMResponse:
        """
        生成补全
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            **kwargs: 其他参数（temperature, max_tokens等）
            
        Returns:
            LLMResponse 响应
        """
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """模型名称"""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """提供商名称"""
        pass
    
    def get_config_for_aider(self) -> dict[str, Any]:
        """
        获取 Aider 所需的环境变量配置
        
        Returns:
            dict 环境变量配置
        """
        return {}
