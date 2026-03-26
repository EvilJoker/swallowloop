"""LLMConfig 模块测试"""

import pytest
from swallowloop.infrastructure.llm import LLMConfig, LLMProvider


class TestLLMConfig:
    """LLMConfig 功能测试"""

    def test_default_config(self):
        """默认配置"""
        config = LLMConfig.default()
        assert config.provider == LLMProvider.IDEFAULT
        assert config.is_default is True

    def test_minimax_config(self):
        """Minimax 配置"""
        config = LLMConfig.minimax(api_key="test-key-123")
        assert config.provider == LLMProvider.MINIMAX
        assert config.model_name == "m2.7"
        assert config.base_url == "https://api.minimaxi.com/v1"
        assert config.api_key == "test-key-123"

    def test_minimax_custom_model(self):
        """Minimax 自定义模型"""
        config = LLMConfig.minimax(api_key="test-key", model_name="custom-model")
        assert config.model_name == "custom-model"

    def test_openai_config(self):
        """OpenAI 配置"""
        config = LLMConfig.openai(api_key="sk-test123")
        assert config.provider == LLMProvider.OPENAI
        assert config.model_name == "gpt-4o"
        assert config.base_url == "https://api.openai.com/v1"

    def test_openai_custom_model(self):
        """OpenAI 自定义模型"""
        config = LLMConfig.openai(api_key="sk-test", model_name="gpt-4o-mini")
        assert config.model_name == "gpt-4o-mini"

    def test_custom_config(self):
        """自定义配置"""
        config = LLMConfig.custom(
            api_key="custom-key",
            base_url="https://custom.api.com/v1",
            model_name="custom-model"
        )
        assert config.provider == LLMProvider.CUSTOM
        assert config.model_name == "custom-model"
        assert config.base_url == "https://custom.api.com/v1"

    def test_is_default(self):
        """is_default 属性"""
        default_config = LLMConfig.default()
        assert default_config.is_default is True

        minimax_config = LLMConfig.minimax(api_key="key")
        assert minimax_config.is_default is False

    def test_to_iflow_auth_info_default(self):
        """默认配置的 iFlow 认证信息"""
        config = LLMConfig.default()
        assert config.to_iflow_auth_info() is None

    def test_to_iflow_auth_info_with_credentials(self):
        """有凭证时的 iFlow 认证信息"""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            api_key="sk-test",
            base_url="https://api.openai.com/v1",
            model_name="gpt-4o",
        )
        auth_info = config.to_iflow_auth_info()
        assert auth_info is not None
        assert auth_info["apiKey"] == "sk-test"
        assert auth_info["baseUrl"] == "https://api.openai.com/v1"
        assert auth_info["modelName"] == "gpt-4o"

    def test_iflow_auth_method_id_default(self):
        """默认配置的认证方式"""
        config = LLMConfig.default()
        assert config.iflow_auth_method_id is None

    def test_iflow_auth_method_id_custom(self):
        """自定义配置的认证方式"""
        config = LLMConfig.openai(api_key="sk-test")
        assert config.iflow_auth_method_id == "openai-compatible"

    def test_repr_masks_api_key(self):
        """repr 隐藏 API key"""
        config = LLMConfig.openai(api_key="sk-1234567890abcdef")
        repr_str = repr(config)
        # API key 应该被部分隐藏，格式是前8后4
        assert "sk-12345...cdef" in repr_str
        assert "sk-1234567890abcdef" not in repr_str

    def test_repr_short_api_key(self):
        """短 API key 用 *** 替代"""
        config = LLMConfig.openai(api_key="short")
        repr_str = repr(config)
        assert "***" in repr_str
