"""独立的 Dashboard 服务入口

可以单独启动 Dashboard 服务，用于查看已有任务状态
"""

import argparse
import logging
from pathlib import Path

from ...infrastructure.config import Settings
from ...infrastructure.persistence import JsonTaskRepository, JsonWorkspaceRepository
from .dashboard import DashboardServer


logger = logging.getLogger(__name__)


def main():
    """Dashboard 独立入口"""
    parser = argparse.ArgumentParser(description="SwallowLoop Dashboard")
    parser.add_argument("--port", type=int, default=8080, help="服务端口 (默认: 8080)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="监听地址 (默认: 0.0.0.0)")
    args = parser.parse_args()
    
    # 加载配置
    try:
        settings = Settings.from_env()
    except ValueError as e:
        print(f"配置错误: {e}")
        print("请确保设置了 GITHUB_TOKEN 和 GITHUB_REPO 环境变量")
        return
    
    # 初始化仓库
    task_repo = JsonTaskRepository(settings.work_dir)
    workspace_repo = JsonWorkspaceRepository(settings.work_dir)
    
    # 创建 Dashboard 服务
    dashboard = DashboardServer(
        task_repository=task_repo,
        workspace_repository=workspace_repo,
        settings=settings,
        port=args.port,
    )
    
    print(f"SwallowLoop Dashboard 已启动: http://localhost:{args.port}")
    print("按 Ctrl+C 退出")
    
    # 运行服务
    dashboard.run_sync()


if __name__ == "__main__":
    main()
