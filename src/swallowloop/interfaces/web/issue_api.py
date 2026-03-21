"""FastAPI Issue API 服务入口"""

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .api.issues import router as issues_router, init_services
from .api.websockets import manager

app = FastAPI(title="SwallowLoop Issue API", version="1.0.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(issues_router, prefix="/api", tags=["issues"])


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.websocket("/ws/execution/{issue_id}")
async def websocket_endpoint(websocket: WebSocket, issue_id: str):
    """WebSocket 执行日志端点"""
    await manager.connect(websocket, issue_id)
    try:
        while True:
            # 保持连接，可以接收客户端消息
            data = await websocket.receive_text()
            # 可以处理客户端消息（如心跳）
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, issue_id)


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """启动服务"""
    # 初始化服务
    init_services()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
