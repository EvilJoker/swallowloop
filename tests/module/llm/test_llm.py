"""LLM 模块测试"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from swallowloop.infrastructure.config import Config
from swallowloop.infrastructure.llm import (
    LLMProviderEnum,
    LLMConfig,
    LLMUsage,
    LLMProviderMinimax,
    init_llm,
    get_llm_instance,
    get_llm_usage,
)


class TestLLMProviderEnum:
    """LLMProviderEnum 测试"""

    def test_enum_values(self):
        """枚举值"""
        assert LLMProviderEnum.OPENAI.value == "openai"
        assert LLMProviderEnum.MINIMAX.value == "minimax"
        assert LLMProviderEnum.CUSTOM.value == "custom"


class TestLLMConfig:
    """LLMConfig 测试"""

    def test_config_creation(self):
        """创建 LLMConfig"""
        config = LLMConfig(
            provider=LLMProviderEnum.MINIMAX,
            api_key="test-key",
            base_url="https://api.minimaxi.com/v1",
            model_name="m2.7",
        )
        assert config.provider == LLMProviderEnum.MINIMAX
        assert config.api_key == "test-key"
        assert config.base_url == "https://api.minimaxi.com/v1"
        assert config.model_name == "m2.7"

    def test_config_optional_fields(self):
        """可选字段默认为 None"""
        config = LLMConfig(provider=LLMProviderEnum.MINIMAX, model_name="m2.7")
        assert config.api_key is None
        assert config.base_url is None


class TestLLMUsage:
    """LLMUsage 测试"""

    def test_usage_creation(self):
        """创建 LLMUsage"""
        now = datetime.now()
        usage = LLMUsage(
            used=100,
            quota=1500,
            last_call=now,
            next_refresh=None,
        )
        assert usage.used == 100
        assert usage.quota == 1500
        assert usage.last_call == now
        assert usage.next_refresh is None

    def test_usage_defaults(self):
        """默认值"""
        usage = LLMUsage()
        assert usage.used == 0
        assert usage.quota == 0
        assert usage.last_call is None
        assert usage.next_refresh is None


class TestLLMProviderMinimax:
    """LLMProviderMinimax 测试"""

    def setup_method(self):
        """每个测试前重置单例"""
        LLMProviderMinimax._instance = None

    def teardown_method(self):
        """每个测试后清理"""
        LLMProviderMinimax._instance = None

    def test_init_without_params(self):
        """构造函数不需参数"""
        Config.load()
        instance = LLMProviderMinimax()
        assert instance._config is not None
        assert instance._usage is not None
        assert isinstance(instance._usage, LLMUsage)

    def test_singleton_set_and_get(self):
        """单例模式"""
        Config.load()
        instance = LLMProviderMinimax.set_instance()
        assert instance is LLMProviderMinimax.get_instance()

    def test_get_config(self):
        """获取配置"""
        Config.load()
        instance = LLMProviderMinimax.set_instance()

        config = instance.get_config()
        assert config is not None
        assert isinstance(config, LLMConfig)
        assert config.provider == LLMProviderEnum.MINIMAX

    def test_get_usage_returns_same_object(self):
        """get_usage 返回同一对象引用"""
        Config.load()
        instance = LLMProviderMinimax.set_instance()

        usage1 = instance.get_usage()
        usage2 = instance.get_usage()
        assert usage1 is usage2  # 同一引用，不是副本

    def test_get_usage_defaults(self):
        """默认使用量"""
        Config.load()
        instance = LLMProviderMinimax.set_instance()

        usage = instance.get_usage()
        assert usage.used == 0
        assert usage.quota == 1500
        assert usage.last_call is None

    def test_load_config(self):
        """从 Config 模块加载配置"""
        Config.load()
        instance = LLMProviderMinimax.set_instance()

        instance.load_config()
        config = instance.get_config()
        assert config.provider == LLMProviderEnum.MINIMAX
        assert config.base_url == "https://api.minimaxi.com/v1"

    def test_get_instance_before_init(self):
        """未初始化时抛出异常"""
        LLMProviderMinimax._instance = None
        with pytest.raises(RuntimeError, match="未初始化"):
            LLMProviderMinimax.get_instance()

    def test_fetch_usage_no_api_key(self):
        """无 API key 时返回默认使用量"""
        Config.load()
        instance = LLMProviderMinimax.set_instance()

        # 确保没有 api_key
        instance._config.api_key = None

        import asyncio
        usage = asyncio.run(instance.fetch_usage())

        assert usage.used == 0
        assert usage.quota == 1500

    @pytest.mark.asyncio
    async def test_fetch_usage_success(self):
        """fetch_usage 成功获取配额"""
        Config.load()
        instance = LLMProviderMinimax.set_instance()
        instance._config.api_key = "test-api-key"  # 设置 API key

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model_remains": [{
                "current_interval_total_count": 1500,
                "current_interval_usage_count": 500,
                "start_time": 1772676000000,
                "end_time": 1772694000000,
            }]
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client_instance

        with patch("swallowloop.infrastructure.llm.LLMProviderMinimax.httpx.AsyncClient", return_value=mock_context):
            usage = await instance.fetch_usage()

        assert usage.used == 1000  # 1500 - 500
        assert usage.quota == 1500
        assert usage.last_call is not None
        assert usage.next_refresh is not None

    @pytest.mark.asyncio
    async def test_fetch_usage_api_error(self):
        """fetch_usage API 错误时返回当前使用量"""
        Config.load()
        instance = LLMProviderMinimax.set_instance()

        with patch("swallowloop.infrastructure.llm.LLMProviderMinimax.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=Exception("Network error"))

            usage = await instance.fetch_usage()

        # 返回当前使用量（未更新）
        assert usage.used == 0
        assert usage.quota == 1500

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """initialize 成功"""
        Config.load()
        instance = LLMProviderMinimax.set_instance()

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            await instance.initialize()

        # 无异常即成功

    @pytest.mark.asyncio
    async def test_initialize_no_api_key(self):
        """无 API key 时跳过初始化"""
        Config.load()
        instance = LLMProviderMinimax.set_instance()
        instance._config.api_key = None

        await instance.initialize()  # 不抛异常

    @pytest.mark.asyncio
    async def test_initialize_failure(self):
        """initialize 失败"""
        Config.load()
        instance = LLMProviderMinimax.set_instance()
        instance._config.api_key = "test-api-key"  # 设置 API key

        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client_instance

        with patch("swallowloop.infrastructure.llm.LLMProviderMinimax.httpx.AsyncClient", return_value=mock_context):
            with pytest.raises(Exception, match="初始化失败"):
                await instance.initialize()


class TestLLMManager:
    """LLM Manager 测试"""

    def setup_method(self):
        """每个测试前重置单例"""
        LLMProviderMinimax._instance = None

    def teardown_method(self):
        """每个测试后清理"""
        LLMProviderMinimax._instance = None

    def test_init_llm(self):
        """初始化 LLM"""
        Config.load()
        instance = init_llm()
        assert instance is not None
        assert isinstance(instance, LLMProviderMinimax)

    def test_get_llm_instance(self):
        """获取 LLM 实例"""
        Config.load()
        init_llm()

        instance = get_llm_instance()
        assert instance is not None
        assert isinstance(instance, LLMProviderMinimax)

    def test_get_llm_usage(self):
        """获取使用量"""
        Config.load()
        init_llm()

        usage = get_llm_usage()
        assert usage is not None
        assert isinstance(usage, LLMUsage)

    def test_get_llm_instance_before_init(self):
        """未初始化时返回 None"""
        LLMProviderMinimax._instance = None
        instance = get_llm_instance()
        assert instance is None

    def test_get_llm_usage_before_init(self):
        """未初始化时返回 None"""
        LLMProviderMinimax._instance = None
        usage = get_llm_usage()
        assert usage is None

    def test_init_llm_singleton(self):
        """多次 init_llm 返回同一实例"""
        Config.load()
        instance1 = init_llm()
        instance2 = init_llm()
        assert instance1 is instance2
