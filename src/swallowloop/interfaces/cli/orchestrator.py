"""DDD 架构的 Orchestrator 实现"""

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

import psutil

from ...application.dto import IssueDTO
from ...application.service import TaskService, ExecutionService
from ...domain.model import Task, TaskState, Comment
from ...domain.repository import TaskRepository, WorkspaceRepository
from ...infrastructure.config import Settings
from ...infrastructure.logger import setup_logging, get_logger
from ...infrastructure.persistence import JsonTaskRepository, JsonWorkspaceRepository
from ...infrastructure.source_control import GitHubSourceControl
from ...infrastructure.agent import IFlowAgent, AiderAgent, Agent
from ...infrastructure.agent.base import ExecutionResult
from ...infrastructure.logging.dashboard_handler import get_dashboard_handler


logger = get_logger(__name__)


class SourceControlAdapter:
    """
    源码控制适配器
    
    将 Infrastructure 层的 GitHubSourceControl 适配到 Application 层的 Protocol 接口
    """
    
    def __init__(self, github_client: GitHubSourceControl):
        self._github = github_client
    
    def get_labeled_issues(self, label: str) -> list[IssueDTO]:
        """获取带标签的 Issue"""
        issues = self._github.get_labeled_issues(label)
        return [
            IssueDTO(
                number=issue.number,
                title=issue.title,
                body=issue.body,
                state=issue.state,
                labels=issue.labels,
                created_at=issue.created_at,
                updated_at=issue.updated_at,
            )
            for issue in issues
        ]
    
    def get_issue_comments(self, issue_number: int) -> list[Comment]:
        """获取 Issue 评论"""
        comments = self._github.get_issue_comments(issue_number)
        return [
            Comment(
                id=comment.id,
                body=comment.body,
                author=comment.author,
                created_at=comment.created_at,
            )
            for comment in comments
        ]
    
    def comment_on_issue(self, issue_number: int, body: str) -> None:
        """在 Issue 上评论"""
        self._github.comment_on_issue(issue_number, body)
    
    def get_clone_url(self) -> str:
        """获取克隆 URL"""
        return self._github.get_clone_url_with_token()
    
    def create_pull_request(
        self,
        branch_name: str,
        title: str,
        body: str,
        base_branch: str = "main",
    ):
        """创建 PR"""
        return self._github.create_pull_request(branch_name, title, body, base_branch)
    
    def get_pull_request(self, pr_number: int):
        """获取 PR"""
        return self._github.get_pull_request(pr_number)
    
    def has_branch(self, branch_name: str) -> bool:
        """检查分支是否存在"""
        return self._github.has_branch(branch_name)
    
    def delete_branch(self, branch_name: str) -> bool:
        """删除远端分支"""
        return self._github.delete_branch(branch_name)


class Orchestrator:
    """
    主调度器
    
    协调 TaskService 和 ExecutionService，实现完整的任务处理流程
    """
    
    def __init__(self, settings: Settings, enable_dashboard: bool = True, dashboard_port: int = 8080):
        self._settings = settings
        self._enable_dashboard = enable_dashboard
        self._dashboard_port = dashboard_port
        
        # 初始化日志
        setup_logging(log_dir=settings.logs_dir)
        
        # 初始化基础设施
        self._task_repo: TaskRepository = JsonTaskRepository(settings.work_dir)
        self._workspace_repo: WorkspaceRepository = JsonWorkspaceRepository(settings.work_dir)
        
        # 初始化 GitHub 客户端
        github_client = GitHubSourceControl(
            token=settings.github_token,
            repo=settings.github_repo,
        )
        self._source_control = SourceControlAdapter(github_client)
        
        # 初始化 Agent
        self._agent = self._create_agent()
        
        # 初始化应用服务
        self._task_service = TaskService(
            task_repository=self._task_repo,
            workspace_repository=self._workspace_repo,
            source_control=self._source_control,
            issue_label=settings.issue_label,
            base_branch=settings.base_branch,
        )
        
        self._execution_service = ExecutionService(
            task_repository=self._task_repo,
            workspace_repository=self._workspace_repo,
            source_control=self._source_control,
            agent=self._agent,
            base_branch=settings.base_branch,
        )
        
        # 初始化 Dashboard 服务
        self._dashboard = None
        if enable_dashboard:
            self._init_dashboard()
        
        self._running = True
    
    def _init_dashboard(self):
        """初始化 Dashboard 服务"""
        from ..web import DashboardServer
        
        self._dashboard = DashboardServer(
            task_repository=self._task_repo,
            workspace_repository=self._workspace_repo,
            settings=self._settings,
            port=self._dashboard_port,
        )
        
        # 启动 Dashboard 服务（在后台进程）
        self._dashboard_process = self._dashboard.start_in_process()
        
        # 设置日志处理器
        dashboard_handler = get_dashboard_handler()
        dashboard_handler.set_emit_callback(self._emit_log_to_dashboard)
        
        logger.info(f"Dashboard 已启动: http://localhost:{self._dashboard_port}")
    
    def _emit_log_to_dashboard(self, issue_number: int, level: str, message: str, source: str):
        """发送日志到 Dashboard"""
        if self._dashboard is None:
            return
        
        # 使用 asyncio 发送（需要在事件循环中运行）
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(
                self._dashboard.emit_log(issue_number, level, message, source)
            )
            loop.close()
        except Exception as e:
            # 静默处理错误，避免影响主流程
            pass
    
    def _create_agent(self) -> Agent:
        """根据配置创建 Agent"""
        if self._settings.agent_type == "iflow":
            from ...infrastructure.agent.iflow import IFlowConfig
            
            config = IFlowConfig(
                timeout=float(self._settings.agent_timeout),
            )
            return IFlowAgent(config, settings=self._settings)
        else:
            from ...infrastructure.agent.aider import AiderConfig
            
            config = AiderConfig(
                model=self._settings.llm_model,
                timeout=self._settings.agent_timeout,
            )
            return AiderAgent(config, settings=self._settings)
    
    def run(self) -> None:
        """主循环"""
        logger.info(f"SwallowLoop 启动 - Agent: {self._agent.name}")
        logger.info(f"仓库: {self._settings.github_repo}")
        logger.info(f"监听标签: {self._settings.issue_label}")
        
        # 检查 Agent 可用性
        available, message = self._agent.check_available()
        if not available:
            logger.error(f"Agent 不可用: {message}")
            sys.exit(1)
        logger.info(f"Agent 状态: {message}")
        
        while self._running:
            try:
                self._tick()
            except KeyboardInterrupt:
                logger.info("收到中断信号，正在退出...")
                self._running = False
            except Exception as e:
                logger.exception(f"运行时错误: {e}")
            
            if self._running:
                time.sleep(self._settings.poll_interval)
        
        # 清理
        self._execution_service.terminate_all_workers()
        logger.info("SwallowLoop 已停止")
    
    def _tick(self) -> None:
        """一次调度周期"""
        logger.debug("轮询开始...")
        
        # 1. 清理过期资源
        self._cleanup_expired()
        
        # 2. 扫描 Issue
        _, tasks_to_abort = self._task_service.scan_issues()
        
        # 3. 处理需要中止的任务（Issue 已关闭）
        for task in tasks_to_abort:
            self._abort_task(task, "Issue 已关闭")
        
        # 4. 处理待执行任务
        pending_tasks = self._task_service.get_pending_tasks()
        for task in pending_tasks:
            self._process_task(task)
        
        # 5. 检查执行中的任务
        in_progress_tasks = self._task_service.get_in_progress_tasks()
        for task in in_progress_tasks:
            self._check_task_result(task)
    
    def _abort_task(self, task: Task, reason: str) -> None:
        """中止任务"""
        logger.info(f"Issue#{task.issue_number} 已中止: {reason}")
        
        # 终止 Worker
        self._execution_service.terminate_worker(task.issue_number)
        
        # 更新任务状态
        self._task_service.abort_task(task, reason)
    
    def _process_task(self, task: Task) -> None:
        """处理单个任务"""
        retry_info = f" (重试 {task.retry_count}/{task._max_retries})" if task.retry_count > 0 else ""
        logger.info(f"处理 Issue#{task.issue_number}: {task.title}{retry_info}")
        
        # 设置当前日志上下文
        dashboard_handler = get_dashboard_handler()
        dashboard_handler.set_current_issue(task.issue_number)
        
        # 根据状态区分处理
        if task.state == TaskState.NEW.value:
            # 新任务：分配工作空间
            workspace = self._task_service.assign_workspace(task)
            logger.info(f"工作空间: {workspace.path}")
        elif task.state == TaskState.PENDING.value:
            # 重试任务：已有工作空间，直接启动
            logger.info(f"重试任务，工作空间: {task.workspace.path if task.workspace else '未知'}")
        
        # 开始任务
        self._task_service.start_task(task)
        
        # 启动 Worker
        self._execution_service.start_worker(task)
        logger.info(f"Worker 已启动")
        
        # 注册 Worker 到 Dashboard
        if self._dashboard and task._worker_pid:
            self._dashboard.register_worker(task.issue_number, task._worker_pid)
    
    def _check_task_result(self, task: Task) -> None:
        """检查任务执行结果"""
        result = self._execution_service.check_worker_result(task)
        
        if result is None:
            # 仍在执行
            return
        
        # 获取工作空间路径
        workspace_path = task.workspace.path if task.workspace else None
        
        logger.info(f"Issue#{task.issue_number} 执行结果: success={result.success}, message={result.message}, files={result.files_changed}")
        
        if result.success:
            # 成功，创建 PR
            try:
                pr = self._execution_service.create_pull_request(task)
                self._task_service.submit_task(task, pr.number, pr.html_url)
                
                # 生成报告
                if workspace_path:
                    self._agent.generate_report(task, workspace_path, result, pr.html_url)
                
                # 评论通知
                message = self._task_service.format_comment(
                    task, 
                    f"已创建 PR #{pr.number}: {pr.html_url}"
                )
                self._task_service.comment_on_issue(task.issue_number, message)
                
                logger.info(f"Issue#{task.issue_number} PR 已创建: {pr.html_url}")
            except Exception as e:
                # PR 创建失败，视为任务失败
                logger.error(f"Issue#{task.issue_number} PR 创建失败: {e}")
                result = ExecutionResult(False, f"PR 创建失败: {e}", result.files_changed)
                # 继续走失败处理逻辑
                if workspace_path:
                    self._agent.generate_report(task, workspace_path, result)
                if task.is_retryable:
                    self._task_service.retry_task(task, result.message)
                else:
                    self._task_service.abort_task(task, result.message)
                    message = self._task_service.format_comment(task, f"执行失败: {result.message}")
                    self._task_service.comment_on_issue(task.issue_number, message)
        else:
            # 生成报告（失败）
            if workspace_path:
                self._agent.generate_report(task, workspace_path, result)
            
            # 失败，检查是否可重试
            if task.is_retryable:
                logger.warning(f"Issue#{task.issue_number} 执行失败，准备重试: {result.message}")
                self._task_service.retry_task(task, result.message)
            else:
                # 已达最大重试次数，中止任务
                logger.error(f"Issue#{task.issue_number} 执行失败（已达最大重试次数）: {result.message}")
                self._task_service.abort_task(task, result.message)
                
                message = self._task_service.format_comment(
                    task,
                    f"执行失败: {result.message}"
                )
                self._task_service.comment_on_issue(task.issue_number, message)
    
    def _cleanup_expired(self) -> None:
        """清理过期资源（已完成/已终止超过7天的任务）"""
        import shutil
        from datetime import datetime, timedelta
        
        # 获取已完成的任务
        completed_tasks = self._task_repo.list_completed()
        
        for task in completed_tasks:
            # 检查是否超过7天
            if task.updated_at:
                age = datetime.now() - task.updated_at
                if age < timedelta(days=7):
                    continue
            else:
                continue
            
            print(f"[Cleanup] 清理过期任务 Issue#{task.issue_number}")
            
            # 1. 删除工作空间目录
            if task.workspace and task.workspace.path.exists():
                try:
                    shutil.rmtree(task.workspace.path)
                    print(f"[Cleanup] 删除工作空间: {task.workspace.path}")
                except Exception as e:
                    print(f"[Cleanup] 删除工作空间失败: {e}")
            
            # 2. 删除远端分支（如果存在）
            if task.branch_name:
                if self._source_control.has_branch(task.branch_name):
                    if self._source_control.delete_branch(task.branch_name):
                        print(f"[Cleanup] 删除远端分支: {task.branch_name}")
            
            # 3. 删除任务记录
            self._task_repo.delete(task.id)
            
            # 4. 删除工作空间记录
            if task.workspace:
                self._workspace_repo.delete(task.workspace.id)


def kill_existing_processes() -> None:
    """杀死已存在的 swallowloop 进程"""
    current_pid = os.getpid()
    killed = False

    for proc in psutil.process_iter(["pid", "exe", "cmdline"]):
        try:
            exe = proc.info.get("exe") or ""
            cmdline = proc.info.get("cmdline") or []
            
            # 跳过 VSCode 扩展进程
            cmdline_str = " ".join(cmdline).lower()
            if "vscode" in cmdline_str or "lsp_server" in cmdline_str:
                continue

            # 检查是否是真正的 swallowloop 入口点
            is_entry = exe.endswith("/swallowloop") or "bin/swallowloop" in exe
            
            if is_entry and proc.info["pid"] != current_pid:
                logger.info(f"终止旧进程: PID={proc.info['pid']}")
                proc.kill()
                killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if killed:
        time.sleep(1)  # 等待进程完全退出


def main() -> None:
    """主入口"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="SwallowLoop - 燕子回环")
    parser.add_argument("--no-dashboard", action="store_true", help="禁用 Web Dashboard")
    parser.add_argument("--port", type=int, default=8080, help="Dashboard 端口号 (默认: 8080)")
    args = parser.parse_args()
    
    # 初始化基本日志（用于启动阶段）
    setup_logging()
    
    kill_existing_processes()
    settings = Settings.from_env()
    orchestrator = Orchestrator(
        settings,
        enable_dashboard=not args.no_dashboard,
        dashboard_port=args.port,
    )
    orchestrator.run()


if __name__ == "__main__":
    main()