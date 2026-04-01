"""MiniMax LLM Provider 实现"""

from datetime import datetime, timedelta

import httpx

from .LLMProviderBase import LLMProviderBase, LLMConfig, LLMUsage, LLMProviderEnum
from ..config import Config

# MiniMax 配额刷新周期（小时）
MINIMAX_QUOTA_REFRESH_HOURS = 5

# MiniMax 默认配额
DEFAULT_MINIMAX_QUOTA = 1500


class LLMProviderMinimax(LLMProviderBase):
    """MiniMax LLM 提供商实现（单例）"""

    _instance: "LLMProviderMinimax | None" = None

    def __init__(self):
        self._config: LLMConfig
        self._usage: LLMUsage = LLMUsage(
            used=0,
            quota=DEFAULT_MINIMAX_QUOTA,
            last_call=None,
            next_refresh=None,
        )
        self.load_config()

    def get_config(self) -> LLMConfig:
        """返回 LLM 配置"""
        return self._config

    def get_usage(self) -> LLMUsage:
        """获取当前 LLM 使用量（不发起请求）"""
        return self._usage

    async def fetch_usage(self) -> LLMUsage:
        """从 MiniMax API 获取真实用量"""
        if not self._config or not self._config.api_key:
            return self._usage

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    "https://api.minimaxi.com/v1/api/openplatform/coding_plan/remains",
                    headers={
                        "Authorization": f"Bearer {self._config.api_key}",
                        "Content-Type": "application/json"
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    model_remains = data.get("model_remains", [])
                    if model_remains:
                        info = model_remains[0]
                        total = info.get("current_interval_total_count", DEFAULT_MINIMAX_QUOTA)
                        remaining = info.get("current_interval_usage_count", 0)
                        used = total - remaining
                        start_ms = info.get("start_time", 0)
                        end_ms = info.get("end_time", 0)

                        start_time = datetime.fromtimestamp(start_ms / 1000) if start_ms else datetime.now()
                        end_time = datetime.fromtimestamp(end_ms / 1000) if end_ms else None

                        # 更新内部状态
                        self._usage = LLMUsage(
                            used=used,
                            quota=total,
                            last_call=start_time,
                            next_refresh=end_time,
                        )
                        return self._usage
        except Exception:
            pass

        return self._usage

    async def initialize(self) -> None:
        """检查 MiniMax API 连接"""
        if not self._config or not self._config.api_key:
            return
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._config.base_url}/models",
                headers={"Authorization": f"Bearer {self._config.api_key}"}
            )
            if response.status_code != 200:
                raise Exception(f"MiniMax API 初始化失败: {response.status_code}")

    def load_config(self) -> None:
        """从 Config 模块加载配置"""
        cfg = Config.get_instance()
        llm_cfg = cfg.get_llm_config()
        self._config = LLMConfig(
            provider=LLMProviderEnum.MINIMAX,
            api_key=llm_cfg.get("api_key"),
            base_url=llm_cfg.get("base_url"),
            model_name=llm_cfg.get("model_name", ""),
        )

    @classmethod
    def get_instance(cls) -> "LLMProviderMinimax":
        """获取单例实例"""
        if cls._instance is None:
            raise RuntimeError("LLMProviderMinimax 未初始化，请先调用 set_instance()")
        return cls._instance

    @classmethod
    def set_instance(cls) -> "LLMProviderMinimax":
        """设置单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
