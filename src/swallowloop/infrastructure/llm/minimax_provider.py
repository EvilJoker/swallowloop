"""Minimax LLM 提供商"""

import os
from typing import Any

from .base import LLMProvider, LLMResponse


class MinimaxProvider(LLMProvider):
    """
    Minimax LLM 提供商
    
    支持 Minimax API
    """
    
    def __init__(
        self,
        api_key: str | None = None,
        group_id: str | None = None,
        model: str = "abab6.5s-chat",
        base_url: str | None = None,
    ):
        self._api_key = api_key or os.getenv("MINIMAX_API_KEY")
        self._group_id = group_id or os.getenv("MINIMAX_GROUP_ID")
        self._model = model
        self._base_url = base_url or os.getenv("MINIMAX_API_BASE_URL", "https://api.minimax.chat/v1")
        
        if not self._api_key:
            raise ValueError("Minimax API key is required")
    
    @property
    def model_name(self) -> str:
        return self._model
    
    @property
    def provider_name(self) -> str:
        return "minimax"
    
    def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs
    ) -> LLMResponse:
        """生成补全"""
        import requests
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = requests.post(
            f"{self._base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self._model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens"),
            },
        )
        
        response.raise_for_status()
        data = response.json()
        
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", self._model),
            usage=data.get("usage"),
            finish_reason=data["choices"][0].get("finish_reason"),
        )
    
    def get_config_for_aider(self) -> dict[str, Any]:
        """获取 Aider 所需的环境变量配置"""
        return {
            "OPENAI_API_KEY": self._api_key,
            "AIDER_OPENAI_API_BASE": self._base_url,
        }
