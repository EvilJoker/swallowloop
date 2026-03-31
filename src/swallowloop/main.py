"""SwallowLoop 入口 - 支持多线程启动"""

import asyncio
import logging
import os
import threading
from pathlib import Path

from .application.service.stage_loop import StageLoop
from .application.service.executor_service import ExecutorService
from .application.service.clean_service import CleanService
from .domain.repository import IssueRepository
from .application.service.worker_pool import ExecutorWorkerPool
from .infrastructure.persistence import InMemoryIssueRepository
from .interfaces.web.issue_api import run_server

logger = logging.getLogger(__name__)


def _run_clean_service(clean_service: "CleanService") -> None:
    """在独立线程中运行 CleanService（使用 run_forever 避免 asyncio.run 阻塞）"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(clean_service.start())
    try:
        loop.run_forever()
    finally:
        loop.close()


def create_services():
    """创建共享服务实例"""
    from .infrastructure.instance_registry import register_instance
    from .interfaces.web.api.websockets import manager
    from .infrastructure.agent import MockAgent, DeerFlowAgent
    from .infrastructure.config import Settings

    # Repository
    repository: IssueRepository = InMemoryIssueRepository()
    register_instance("repository", repository)

    # WebSocket Manager
    register_instance("ws_manager", manager)

    # Settings
    try:
        settings = Settings.from_env()
    except ValueError:
        # 独立运行时使用默认配置
        settings = None

    register_instance("settings", settings)

    # Agent
    agent_type = os.getenv("AGENT_TYPE", "mock")
    deerflow_base_url = os.getenv("DEERFLOW_BASE_URL", "http://localhost:2024")
    if agent_type == "deerflow":
        agent = DeerFlowAgent(base_url=deerflow_base_url)
    else:
        agent = MockAgent(delay_seconds=5.0)
    register_instance("agent", agent)

    # CleanService (仅 DeerFlow 模式需要)
    if agent_type == "deerflow":
        clean_service = CleanService(repository=repository, base_url=deerflow_base_url, interval_hours=1)
        register_instance("clean_service", clean_service)
    else:
        clean_service = None
    register_instance("clean_service", clean_service)

    # Executor (注入 ws_manager 用于广播)
    executor = ExecutorService(repository=repository, agent=agent, agent_type=agent_type, ws_manager=manager)
    register_instance("executor", executor)

    # WorkerPool (max_workers=3)
    worker_pool = ExecutorWorkerPool(executor=executor, max_workers=3)
    register_instance("worker_pool", worker_pool)

    return repository, executor, worker_pool, agent, settings, clean_service


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
    repository, executor, worker_pool, agent, settings, clean_service = create_services()

    # 2. 创建 StageLoop
    stage_loop = StageLoop(
        repository=repository,
        worker_pool=worker_pool,
        executor=executor,
        interval=5,  # 5 秒一次
    )

    # 2.5 启动 CleanService（仅 DeerFlow 模式）
    if clean_service:
        clean_thread = threading.Thread(
            target=lambda: _run_clean_service(clean_service),
            daemon=True,
            name="CleanService"
        )
        clean_thread.start()
        logger.info("CleanService 已启动（后台运行）")

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
