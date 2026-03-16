"""DeepSeek LLM 提供商"""

import os
from typing import Any

from .base import LLMProvider, LLMResponse


class DeepSeekProvider(LLMProvider):
    """
    DeepSeek LLM 提供商
    
    支持 DeepSeek API
    """
    
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "deepseek-chat",
        base_url: str | None = None,
    ):
        self._api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self._model = model
        self._base_url = base_url or os.getenv("DEEPSEEK_API_BASE_URL", "https://api.deepseek.com/v1")
        
        if not self._api_key:
            raise ValueError("DeepSeek API key is required")
    
    @property
    def model_name(self) -> str:
        return self._model
    
    @property
    def provider_name(self) -> str:
        return "deepseek"
    
    def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs
    ) -> LLMResponse:
        """生成补全"""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package is required: pip install openai")
        
        client = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens"),
        )
        
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            } if response.usage else None,
            finish_reason=response.choices[0].finish_reason,
        )
    
    def get_config_for_aider(self) -> dict[str, Any]:
        """获取 Aider 所需的环境变量配置"""
        return {
            "OPENAI_API_KEY": self._api_key,
            "AIDER_OPENAI_API_BASE": self._base_url,
        }
