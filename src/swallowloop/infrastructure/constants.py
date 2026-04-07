"""全局常量定义"""

# DeerFlow 配置
DEFAULT_DEERFLOW_BASE_URL = "http://localhost:2026"

# HTTP 超时配置（秒）
class HttpTimeout:
    DEFAULT = 30.0
    LONG_RUNNING = 300.0  # 5 分钟
    HEALTH_CHECK = 5.0
    SHORT = 10.0

# 轮询配置
POLL_INTERVAL_SECONDS = 20
MAX_EXECUTE_TIMEOUT_SECONDS = 1800  # 30 分钟

# MiniMax LLM 配置
MINIMAX_QUOTA_REFRESH_HOURS = 5
DEFAULT_MINIMAX_QUOTA = 1500

# 敏感日志脱敏关键词
SENSITIVE_KEYS = [
    "api_key",
    "token",
    "secret",
    "password",
    "authorization",
    "github_token",
]
