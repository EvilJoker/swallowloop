"""日志工具函数"""
import re
from .constants import SENSITIVE_KEYS


def sanitize_log_message(msg: str) -> str:
    """
    脱敏日志消息，隐藏敏感信息

    Args:
        msg: 原始日志消息

    Returns:
        脱敏后的消息
    """
    result = msg
    for key in SENSITIVE_KEYS:
        # 匹配各种敏感格式: api_key=xxx, "api_key": "xxx", apiKey: xxx
        patterns = [
            rf'{key}=["\']?[^"\'\s]+["\']?',
            rf'"{key}":\s*"[^"]+"',
            rf'"{key}":\s*\'[^\']+\'',
        ]
        for pattern in patterns:
            result = re.sub(pattern, f'{key}=[REDACTED]', result, flags=re.IGNORECASE)
    return result
