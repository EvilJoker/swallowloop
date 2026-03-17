"""FastAPI 应用工厂"""

from pathlib import Path
from typing import Callable

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .routes import router


def create_app(
    task_repo_factory: Callable,
    workspace_repo_factory: Callable,
    logs_dir: Path | None = None,
) -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="SwallowLoop Dashboard",
        description="任务可视化与管理面板",
        version="0.1.0",
    )
    
    # 存储依赖工厂
    app.state.task_repo_factory = task_repo_factory
    app.state.workspace_repo_factory = workspace_repo_factory
    app.state.logs_dir = logs_dir or (Path.home() / ".swallowloop" / "logs")
    
    # 模板目录
    templates_dir = Path(__file__).parent / "templates"
    app.state.templates = Jinja2Templates(directory=str(templates_dir))
    
    # 注册路由
    app.include_router(router)
    
    # 静态文件（用于自定义样式）
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    return app
