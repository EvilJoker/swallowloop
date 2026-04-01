"""DeerFlow HTTP 客户端封装"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class DeerFlowClient:
    """DeerFlow HTTP 客户端 - 封装 httpx 调用"""

    def __init__(self, base_url: str = "http://localhost:2026", timeout: float = 300.0):
        """
        Args:
            base_url: DeerFlow 服务地址
            timeout: 请求超时时间（秒）
        """
        self._base_url = base_url
        self._timeout = timeout

    def _create_client(self) -> httpx.AsyncClient:
        """创建 HTTP 客户端"""
        return httpx.AsyncClient(timeout=self._timeout)

    async def delete_thread(self, thread_id: str) -> bool:
        """
        删除 Thread

        Args:
            thread_id: Thread ID

        Returns:
            bool: 是否删除成功
        """
        client = self._create_client()
        try:
            async with client:
                response = await client.delete(f"{self._base_url}/threads/{thread_id}")
                if response.status_code in [200, 204, 404]:
                    logger.info(f"DeerFlow Thread 删除成功: {thread_id}")
                    return True
                else:
                    logger.warning(f"DeerFlow Thread 删除失败: {response.status_code}")
                    return False
        except Exception as e:
            logger.warning(f"DeerFlow Thread 删除异常: {e}")
            return False

    async def create_thread(self, metadata: dict[str, Any] | None = None) -> str | None:
        """
        创建 Thread

        Args:
            metadata: 线程元数据

        Returns:
            str: thread_id 或 None
        """
        client = self._create_client()
        try:
            async with client:
                response = await client.post(
                    f"{self._base_url}/threads",
                    json={"metadata": metadata or {}}
                )
                if response.status_code in [200, 201]:
                    result = response.json()
                    return result.get("thread_id")
                logger.warning(f"DeerFlow Thread 创建失败: {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"DeerFlow Thread 创建异常: {e}")
            return None

    async def send_message(self, thread_id: str, message: str) -> dict[str, Any] | None:
        """
        发送消息到 Thread

        Args:
            thread_id: Thread ID
            message: 消息内容

        Returns:
            dict: 响应数据或 None
        """
        client = self._create_client()
        try:
            async with client:
                response = await client.post(
                    f"{self._base_url}/threads/{thread_id}/runs",
                    json={
                        "assistant_id": "lead_agent",
                        "input": {
                            "messages": [{"role": "user", "content": message}]
                        },
                        "stream_mode": "values"
                    },
                    timeout=300.0
                )
                if response.status_code in [200, 201]:
                    return response.json()
                logger.warning(f"DeerFlow 消息发送失败: {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"DeerFlow 消息发送异常: {e}")
            return None

    async def health_check(self) -> tuple[bool, str | None]:
        """
        健康检查

        Returns:
            tuple: (是否在线, 版本号)
        """
        client = self._create_client()
        try:
            async with client:
                response = await client.get(f"{self._base_url}/api/langgraph/info")
                if response.status_code == 200:
                    data = response.json()
                    return True, data.get("version")
                return False, None
        except Exception:
            return False, None
