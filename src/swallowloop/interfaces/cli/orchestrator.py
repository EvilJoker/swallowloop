"""DDD 架构的 Orchestrator 实现"""

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
from ...infrastructure.persistence import JsonTaskRepository, JsonWorkspaceRepository
from ...infrastructure.source_control import GitHubSourceControl
from ...infrastructure.agent import IFlowAgent, AiderAgent, Agent


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


class Orchestrator:
    """
    主调度器
    
    协调 TaskService 和 ExecutionService，实现完整的任务处理流程
    """
    
    def __init__(self, settings: Settings):
        self._settings = settings
        
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
        
        self._running = True
    
    def _create_agent(self) -> Agent:
        """根据配置创建 Agent"""
        if self._settings.agent_type == "iflow":
            from ...infrastructure.agent.iflow import IFlowConfig
            
            config = IFlowConfig(
                timeout=float(self._settings.agent_timeout),
            )
            return IFlowAgent(config)
        else:
            from ...infrastructure.agent.aider import AiderConfig
            
            config = AiderConfig(
                model=self._settings.llm_model,
                timeout=self._settings.agent_timeout,
            )
            return AiderAgent(config)
    
    def run(self) -> None:
        """主循环"""
        print(f"[SwallowLoop] 启动 - Agent: {self._agent.name}")
        print(f"[SwallowLoop] 仓库: {self._settings.github_repo}")
        print(f"[SwallowLoop] 监听标签: {self._settings.issue_label}")
        
        # 检查 Agent 可用性
        available, message = self._agent.check_available()
        if not available:
            print(f"[ERROR] Agent 不可用: {message}")
            sys.exit(1)
        print(f"[SwallowLoop] Agent 状态: {message}")
        
        while self._running:
            try:
                self._tick()
            except KeyboardInterrupt:
                print("\n[SwallowLoop] 收到中断信号，正在退出...")
                self._running = False
            except Exception as e:
                print(f"[ERROR] {e}")
            
            if self._running:
                time.sleep(self._settings.poll_interval)
        
        # 清理
        self._execution_service.terminate_all_workers()
        print("[SwallowLoop] 已停止")
    
    def _tick(self) -> None:
        """一次调度周期"""
        # 1. 扫描 Issue
        self._task_service.scan_issues()
        
        # 2. 处理待执行任务
        pending_tasks = self._task_service.get_pending_tasks()
        for task in pending_tasks:
            self._process_task(task)
        
        # 3. 检查执行中的任务
        in_progress_tasks = self._task_service.get_in_progress_tasks()
        for task in in_progress_tasks:
            self._check_task_result(task)
    
    def _process_task(self, task: Task) -> None:
        """处理单个任务"""
        print(f"[Task] 处理 Issue#{task.issue_number}: {task.title}")
        
        # 分配工作空间
        workspace = self._task_service.assign_workspace(task)
        print(f"[Task] 工作空间: {workspace.path}")
        
        # 开始任务
        self._task_service.start_task(task)
        
        # 启动 Worker
        self._execution_service.start_worker(task)
        print(f"[Task] Worker 已启动")
    
    def _check_task_result(self, task: Task) -> None:
        """检查任务执行结果"""
        result = self._execution_service.check_worker_result(task)
        
        if result is None:
            # 仍在执行
            return
        
        if result.success:
            # 成功，创建 PR
            pr = self._execution_service.create_pull_request(task)
            self._task_service.submit_task(task, pr.number, pr.html_url)
            
            # 评论通知
            message = self._task_service.format_comment(
                task, 
                f"已创建 PR #{pr.number}: {pr.html_url}"
            )
            self._task_service.comment_on_issue(task.issue_number, message)
            
            print(f"[Task] Issue#{task.issue_number} PR 已创建: {pr.html_url}")
        else:
            # 失败
            self._task_service.abort_task(task, result.message)
            
            message = self._task_service.format_comment(
                task,
                f"执行失败: {result.message}"
            )
            self._task_service.comment_on_issue(task.issue_number, message)
            
            print(f"[Task] Issue#{task.issue_number} 失败: {result.message}")


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
                print(f"[KILL] 终止旧进程: PID={proc.info['pid']}")
                proc.kill()
                killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if killed:
        time.sleep(1)  # 等待进程完全退出


def main() -> None:
    """主入口"""
    kill_existing_processes()
    settings = Settings.from_env()
    orchestrator = Orchestrator(settings)
    orchestrator.run()


if __name__ == "__main__":
    main()
