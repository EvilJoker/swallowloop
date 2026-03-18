"""Web Dashboard 服务 - 提供 REST API 和 WebSocket 实时日志"""

import asyncio
import json
import logging
import multiprocessing
import os
import threading
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from ...domain.model import Task, TaskState
from ...domain.repository import TaskRepository, WorkspaceRepository
from ...infrastructure.config import Settings


logger = logging.getLogger(__name__)


@dataclass
class TaskSummary:
    """任务摘要 - 用于前端展示"""
    task_id: str
    issue_number: int
    title: str
    description: str
    state: str
    task_type: str
    branch_name: str
    retry_count: int
    max_retries: int
    created_at: str
    updated_at: str
    started_at: str | None = None
    pr_url: str | None = None
    pr_number: int | None = None
    workspace_path: str | None = None
    is_active: bool = True
    is_retryable: bool = True
    worker_pid: int | None = None


@dataclass
class SessionLog:
    """Session 日志条目"""
    timestamp: str
    level: str
    message: str
    source: str = "agent"


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = defaultdict(list)
        self.log_buffers: dict[int, list[dict]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, issue_number: int):
        """接受 WebSocket 连接"""
        await websocket.accept()
        async with self._lock:
            self.active_connections[issue_number].append(websocket)
            # 发送历史日志
            for log in self.log_buffers.get(issue_number, [])[-100:]:  # 最近100条
                await websocket.send_json(log)
    
    async def disconnect(self, websocket: WebSocket, issue_number: int):
        """断开 WebSocket 连接"""
        async with self._lock:
            if websocket in self.active_connections.get(issue_number, []):
                self.active_connections[issue_number].remove(websocket)
    
    async def broadcast(self, issue_number: int, message: dict):
        """广播消息到特定任务的所有连接"""
        async with self._lock:
            # 缓存日志
            self.log_buffers[issue_number].append(message)
            # 限制缓存大小
            if len(self.log_buffers[issue_number]) > 500:
                self.log_buffers[issue_number] = self.log_buffers[issue_number][-200:]
            
            # 广播
            for connection in self.active_connections.get(issue_number, []):
                try:
                    await connection.send_json(message)
                except Exception:
                    pass
    
    async def broadcast_all(self, message: dict):
        """广播消息到所有连接"""
        async with self._lock:
            for connections in self.active_connections.values():
                for connection in connections:
                    try:
                        await connection.send_json(message)
                    except Exception:
                        pass


class DashboardServer:
    """Web Dashboard 服务"""
    
    def __init__(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        settings: Settings,
        port: int = 8080,
    ):
        self._task_repo = task_repository
        self._workspace_repo = workspace_repository
        self._settings = settings
        self._port = port
        self._manager = ConnectionManager()
        
        # 创建 FastAPI 应用
        self._app = FastAPI(
            title="SwallowLoop Dashboard",
            description="SwallowLoop 任务管理面板",
            version="0.1.0",
        )
        
        # Session 输出跟踪
        self._session_outputs: dict[int, list[str]] = defaultdict(list)
        self._worker_pids: dict[int, int] = {}  # issue_number -> worker_pid
        
        self._setup_routes()
    
    def _setup_routes(self):
        """设置路由"""
        
        # 静态文件服务
        static_dir = Path(__file__).parent / "static"
        static_dir.mkdir(exist_ok=True)
        self._app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        
        @self._app.get("/", response_class=HTMLResponse)
        async def index():
            """主页 - 任务列表"""
            html_path = static_dir / "index.html"
            if html_path.exists():
                return FileResponse(html_path)
            return HTMLResponse(self._get_default_html())
        
        @self._app.get("/api/tasks")
        async def list_tasks():
            """获取所有任务列表"""
            tasks = self._task_repo.list_all()
            summaries = [self._task_to_summary(task) for task in tasks]
            # 按更新时间倒序
            summaries.sort(key=lambda x: x.updated_at, reverse=True)
            return {"tasks": [asdict(s) for s in summaries]}
        
        @self._app.get("/api/tasks/{issue_number}")
        async def get_task(issue_number: int):
            """获取单个任务详情"""
            task = self._task_repo.get_by_issue(issue_number)
            if not task:
                raise HTTPException(status_code=404, detail="任务不存在")
            return {"task": asdict(self._task_to_summary(task))}
        
        @self._app.get("/api/tasks/{issue_number}/logs")
        async def get_task_logs(issue_number: int):
            """获取任务日志历史"""
            logs = self._manager.log_buffers.get(issue_number, [])
            return {"logs": logs[-100:]}  # 最近100条
        
        @self._app.websocket("/ws/tasks/{issue_number}")
        async def task_websocket(websocket: WebSocket, issue_number: int):
            """WebSocket 实时日志"""
            await self._manager.connect(websocket, issue_number)
            try:
                while True:
                    # 保持连接，等待消息
                    data = await websocket.receive_text()
                    # 可以处理客户端发来的命令
                    try:
                        msg = json.loads(data)
                        if msg.get("type") == "ping":
                            await websocket.send_json({"type": "pong"})
                    except json.JSONDecodeError:
                        pass
            except WebSocketDisconnect:
                await self._manager.disconnect(websocket, issue_number)
        
        @self._app.websocket("/ws/dashboard")
        async def dashboard_websocket(websocket: WebSocket):
            """Dashboard 全局 WebSocket - 任务状态变更通知"""
            await websocket.accept()
            try:
                while True:
                    data = await websocket.receive_text()
                    try:
                        msg = json.loads(data)
                        if msg.get("type") == "ping":
                            await websocket.send_json({"type": "pong"})
                    except json.JSONDecodeError:
                        pass
            except WebSocketDisconnect:
                pass
        
        @self._app.get("/api/stats")
        async def get_stats():
            """获取统计信息"""
            tasks = self._task_repo.list_all()
            stats = {
                "total": len(tasks),
                "active": len([t for t in tasks if t.is_active]),
                "completed": len([t for t in tasks if t.state == TaskState.COMPLETED.value]),
                "aborted": len([t for t in tasks if t.state == TaskState.ABORTED.value]),
                "in_progress": len([t for t in tasks if t.state == TaskState.IN_PROGRESS.value]),
                "pending": len([t for t in tasks if t.state == TaskState.PENDING.value]),
            }
            return stats
        
        @self._app.get("/api/sessions")
        async def list_sessions():
            """获取活跃的 Session 列表"""
            in_progress_tasks = self._task_repo.list_active()
            sessions = []
            for task in in_progress_tasks:
                if task.state == TaskState.IN_PROGRESS.value:
                    sessions.append({
                        "issue_number": task.issue_number,
                        "title": task.title,
                        "started_at": task.started_at.isoformat() if task.started_at else None,
                        "worker_pid": self._worker_pids.get(task.issue_number),
                    })
            return {"sessions": sessions}
    
    def _task_to_summary(self, task: Task) -> TaskSummary:
        """将 Task 转换为 TaskSummary"""
        return TaskSummary(
            task_id=str(task.id),
            issue_number=task.issue_number,
            title=task.title,
            description=task.description,
            state=task.state,
            task_type=task.task_type.value,
            branch_name=task.branch_name,
            retry_count=task.retry_count,
            max_retries=task._max_retries,
            created_at=task.created_at.isoformat() if task.created_at else "",
            updated_at=task.updated_at.isoformat() if task.updated_at else "",
            started_at=task.started_at.isoformat() if task.started_at else None,
            pr_url=task.pr.html_url if task.pr else None,
            pr_number=task.pr.number if task.pr else None,
            workspace_path=str(task.workspace.path) if task.workspace else None,
            is_active=task.is_active,
            is_retryable=task.is_retryable,
            worker_pid=self._worker_pids.get(task.issue_number),
        )
    
    def _get_default_html(self) -> str:
        """获取默认 HTML 页面"""
        return """<!DOCTYPE html>
<html>
<head><title>SwallowLoop Dashboard</title></head>
<body><h1>SwallowLoop Dashboard</h1><p>Loading...</p></body>
</html>"""
    
    def register_worker(self, issue_number: int, pid: int):
        """注册 Worker 进程"""
        self._worker_pids[issue_number] = pid
    
    def unregister_worker(self, issue_number: int):
        """注销 Worker 进程"""
        self._worker_pids.pop(issue_number, None)
    
    async def emit_log(self, issue_number: int, level: str, message: str, source: str = "agent"):
        """发送日志到前端"""
        log_entry = {
            "type": "log",
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "source": source,
        }
        await self._manager.broadcast(issue_number, log_entry)
    
    async def emit_status_change(self, issue_number: int, old_state: str, new_state: str):
        """发送状态变更通知"""
        message = {
            "type": "status_change",
            "issue_number": issue_number,
            "old_state": old_state,
            "new_state": new_state,
            "timestamp": datetime.now().isoformat(),
        }
        await self._manager.broadcast(issue_number, message)
        await self._manager.broadcast_all(message)
    
    def run_sync(self):
        """同步运行服务（用于子进程）"""
        uvicorn.run(self._app, host="0.0.0.0", port=self._port, log_level="warning")
    
    def start_in_thread(self):
        """在后台线程启动服务"""
        def run():
            uvicorn.run(self._app, host="0.0.0.0", port=self._port, log_level="warning")
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        logger.info(f"Dashboard 服务已启动: http://localhost:{self._port}")
        return thread
    
    def start_in_process(self):
        """在后台进程启动服务"""
        process = multiprocessing.Process(
            target=self.run_sync,
            daemon=True,
        )
        process.start()
        logger.info(f"Dashboard 服务已启动: http://localhost:{self._port}")
        return process
