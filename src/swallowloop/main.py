"""SwallowLoop 入口 - 支持多线程启动"""

import logging
import threading
from pathlib import Path

from .application.service.stage_loop import StageLoop
from .application.service.executor_service import ExecutorService
from .domain.repository import IssueRepository
from .infrastructure.executor.worker_pool import ExecutorWorkerPool
from .infrastructure.persistence import InMemoryIssueRepository
from .interfaces.web.issue_api import run_server

logger = logging.getLogger(__name__)


def create_services():
    """创建共享服务实例"""
    from .infrastructure.instance_registry import register_instance
    from .interfaces.web.api.websockets import manager

    # Repository
    repository: IssueRepository = InMemoryIssueRepository()
    register_instance("repository", repository)

    # WebSocket Manager
    register_instance("ws_manager", manager)

    # Executor (注入 ws_manager 用于广播)
    executor = ExecutorService(repository=repository, agent_type="mock", ws_manager=manager)
    register_instance("executor", executor)

    # WorkerPool (max_workers=3)
    worker_pool = ExecutorWorkerPool(executor=executor, max_workers=3)
    register_instance("worker_pool", worker_pool)

    return repository, executor, worker_pool


def main(port: int = 9500):
    """主入口 - 启动 StageLoop 和 Web 服务器"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger.info("=" * 50)
    logger.info("SwallowLoop 启动")
    logger.info("=" * 50)

    # 1. 创建共享服务
    repository, executor, worker_pool = create_services()

    # 2. 创建 StageLoop
    stage_loop = StageLoop(
        repository=repository,
        worker_pool=worker_pool,
        interval=5,  # 5 秒一次
    )

    # 3. 在后台线程启动 Web 服务器
    web_thread = threading.Thread(
        target=run_server,
        kwargs={"port": port},
        daemon=True,
        name="WebServer"
    )
    web_thread.start()
    logger.info(f"Web 服务器已启动（端口 {port}）")

    # 4. 主线程运行 StageLoop（阻塞）
    logger.info("StageLoop 启动，每 5 秒扫描一次")
    try:
        stage_loop.start()
    except KeyboardInterrupt:
        logger.info("接收到停止信号")
    finally:
        worker_pool.shutdown()
        logger.info("SwallowLoop 已停止")


if __name__ == "__main__":
    main()
