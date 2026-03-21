"""WebSocket 执行日志"""

from fastapi import WebSocket, WebSocketDisconnect
from collections import defaultdict


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, issue_id: str):
        await websocket.accept()
        self.active_connections[issue_id].append(websocket)

    def disconnect(self, websocket: WebSocket, issue_id: str):
        if websocket in self.active_connections[issue_id]:
            self.active_connections[issue_id].remove(websocket)

    async def send_log(self, issue_id: str, log: dict):
        for connection in self.active_connections.get(issue_id, []):
            try:
                await connection.send_json(log)
            except Exception:
                pass

    async def broadcast(self, issue_id: str, message: str):
        """广播消息到所有连接"""
        for connection in self.active_connections.get(issue_id, []):
            try:
                await connection.send_text(message)
            except Exception:
                pass


# 全局连接管理器实例
manager = ConnectionManager()
