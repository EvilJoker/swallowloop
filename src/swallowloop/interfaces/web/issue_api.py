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


def run_server(host: str = "0.0.0.0", port: int = 8000, repository=None):
    """启动服务

    Args:
        host: 监听地址
        port: 监听端口
        repository: 可选，共享的 IssueRepository 实例
    """
    if repository is not None:
        _inject_repository(repository)
    else:
        init_services()
    # 单进程模式运行（不设置 workers 参数）
    # 这样 _inject_repository 设置的全局变量可以跨请求共享
    uvicorn.run(app, host=host, port=port)


def _inject_repository(repository):
    """注入共享 repository 到 API 服务"""
    import os
    from ...application.service import IssueService, ExecutorService
    from ...domain.repository import IssueRepository
    from .api import issues as issues_module

    # 创建 ExecutorService（不使用 agent_type，因为 mock 已经在 executor 中处理）
    executor = ExecutorService(repository=repository, agent_type="mock")
    issue_service = IssueService(repository=repository, executor=executor)

    issues_module._issue_service = issue_service
    issues_module._executor_service = executor


if __name__ == "__main__":
    run_server()
