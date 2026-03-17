"""Web Dashboard 独立启动入口"""

import argparse
import logging
from pathlib import Path

from ...infrastructure.config import Settings
from ...infrastructure.persistence import JsonTaskRepository, JsonWorkspaceRepository
from .server import run_web_server


logger = logging.getLogger(__name__)


def main() -> None:
    """Web Dashboard 启动入口"""
    parser = argparse.ArgumentParser(
        description="SwallowLoop Web Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="监听地址 (默认: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="监听端口 (默认: 8080)",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="工作目录",
    )
    
    args = parser.parse_args()
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    
    # 加载配置
    try:
        settings = Settings.from_env()
    except ValueError as e:
        logger.error(str(e))
        return
    
    work_dir = args.work_dir or settings.work_dir or Path.home() / ".swallowloop"
    
    def task_repo_factory():
        return JsonTaskRepository(work_dir)
    
    def workspace_repo_factory():
        return JsonWorkspaceRepository(work_dir)
    
    logger.info(f"启动 Web Dashboard: http://{args.host}:{args.port}")
    run_web_server(
        task_repo_factory=task_repo_factory,
        workspace_repo_factory=workspace_repo_factory,
        host=args.host,
        port=args.port,
        logs_dir=settings.logs_dir,
    )


if __name__ == "__main__":
    main()
