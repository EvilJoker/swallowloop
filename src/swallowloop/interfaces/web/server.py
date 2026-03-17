"""Web Dashboard 服务"""

import asyncio
import logging
import multiprocessing
from pathlib import Path
from typing import Callable

import uvicorn

from .app import create_app


logger = logging.getLogger(__name__)


def run_web_server(
    task_repo_factory: Callable,
    workspace_repo_factory: Callable,
    host: str = "0.0.0.0",
    port: int = 8080,
    logs_dir: Path | None = None,
) -> None:
    """
    运行 Web Dashboard 服务
    
    Args:
        task_repo_factory: 任务仓库工厂函数
        workspace_repo_factory: 工作空间仓库工厂函数
        host: 监听地址
        port: 监听端口
        logs_dir: 日志目录
    """
    app = create_app(
        task_repo_factory=task_repo_factory,
        workspace_repo_factory=workspace_repo_factory,
        logs_dir=logs_dir,
    )
    
    logger.info(f"Web Dashboard 启动: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")


def start_web_server_process(
    task_repo_factory: Callable,
    workspace_repo_factory: Callable,
    host: str = "0.0.0.0",
    port: int = 8080,
    logs_dir: Path | None = None,
) -> multiprocessing.Process:
    """
    在后台进程中启动 Web Dashboard 服务
    
    Returns:
        Process 对象
    """
    process = multiprocessing.Process(
        target=run_web_server,
        args=(task_repo_factory, workspace_repo_factory, host, port, logs_dir),
        daemon=True,
    )
    process.start()
    logger.info(f"Web Dashboard 进程已启动: PID={process.pid}")
    return process
