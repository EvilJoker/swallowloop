"""FastAPI Issue API 服务入口"""

import os
import signal
import sys
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .api.issues import router as issues_router, init_services
from .api.deerflow import router as deerflow_router
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
app.include_router(deerflow_router, prefix="/api", tags=["deerflow"])


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/api/admin/restart")
async def restart_backend():
    """重启后端（优雅退出，依赖 run.sh watchdog 自动拉起）"""
    import os
    import signal
    import time

    # 获取当前进程 PID
    pid = os.getpid()
    print(f"收到重启请求，PID: {pid}，{WATCHDOG_INTERVAL}秒后退出...")
    sys.stdout.flush()

    # 延迟退出，给前端响应时间
    def delayed_exit():
        time.sleep(WATCHDOG_INTERVAL)
        # 使用 SIGTERM 优雅退出
        os.kill(pid, signal.SIGTERM)

    import threading
    threading.Thread(target=delayed_exit, daemon=True).start()

    return {"status": "ok", "message": f"后端将在{WATCHDOG_INTERVAL}秒后重启"}


# 全局变量（由 main.py 设置）
WATCHDOG_INTERVAL = 5  # 默认 5 秒，前端会轮询


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


@app.websocket("/ws/issues")
async def ws_issues(websocket: WebSocket):
    """WebSocket Issue 列表广播端点"""
    # 手动接受连接，绕过 Origin 检查
    await websocket.accept()
    manager.active_connections["issues"].append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        if websocket in manager.active_connections["issues"]:
            manager.active_connections["issues"].remove(websocket)


def run_server(host: str = "0.0.0.0", port: int = 8000, repository=None):
    """启动服务

    Args:
        host: 监听地址
        port: 监听端口
        repository: 已废弃，使用注册表替代
    """
    # 从注册表获取实例初始化服务
    init_services()

    # 设置全局退出延迟（与 run.sh watchdog 间隔一致）
    global WATCHDOG_INTERVAL
    WATCHDOG_INTERVAL = 30

    # 单进程模式运行，禁用 WebSocket Origin 检查
    uvicorn.run(
        app,
        host=host,
        port=port,
        ws='websockets',
        timeout_keep_alive=5,
        log_level='info'
    )


if __name__ == "__main__":
    run_server()
