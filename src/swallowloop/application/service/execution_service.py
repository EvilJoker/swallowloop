"""执行应用服务"""

import logging
import multiprocessing
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol

from ...domain.model import Task, Workspace, PullRequest
from ...domain.repository import TaskRepository, WorkspaceRepository
from ...infrastructure.agent import ExecutionResult


logger = logging.getLogger(__name__)


class AgentPort(Protocol):
    """Agent 端口"""
    @property
    def name(self) -> str: ...
    def execute(self, task: Task, workspace_path: Path) -> ExecutionResult: ...
    @staticmethod
    def check_available() -> tuple[bool, str]: ...


class SourceControlPort(Protocol):
    """源码控制端口"""
    def create_pull_request(
        self,
        branch_name: str,
        title: str,
        body: str,
        base_branch: str = "main",
    ) -> "PullRequestInfo": ...
    def get_pull_request(self, pr_number: int) -> "PullRequestInfo": ...


class PullRequestInfo:
    """PR 信息"""
    def __init__(self, number: int, html_url: str, branch_name: str, title: str, body: str = ""):
        self.number = number
        self.html_url = html_url
        self.branch_name = branch_name
        self.title = title
        self.body = body


class ExecutionService:
    """
    执行应用服务
    
    负责任务的执行和监控
    """
    
    MONITOR_INTERVAL = 600  # 监控间隔：10分钟
    
    def __init__(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        source_control: SourceControlPort,
        agent: AgentPort,
        base_branch: str = "main",
    ):
        self._task_repo = task_repository
        self._workspace_repo = workspace_repository
        self._source_control = source_control
        self._agent = agent
        self._base_branch = base_branch
        
        # Worker 进程管理
        self._worker_processes: dict[int, multiprocessing.Process] = {}
        self._last_monitor_time: datetime | None = None
    
    def start_worker(self, task: Task) -> None:
        """启动 Worker 进程"""
        workspace = self._workspace_repo.get(task.issue_number)
        if not workspace:
            raise ValueError(f"工作空间不存在: Issue#{task.issue_number}")
        
        # 启动子进程
        process = multiprocessing.Process(
            target=self._worker_main,
            args=(task, workspace.path, self._agent, self._source_control, self._base_branch),
        )
        process.start()
        
        self._worker_processes[task.issue_number] = process
        task._worker_pid = process.pid
        task._started_at = datetime.now()
        
        logger.info(f"Worker 进程已启动: Issue#{task.issue_number}, PID={process.pid}")
    
    @staticmethod
    def _worker_main(
        task: Task,
        workspace_path: Path,
        agent: AgentPort,
        source_control: SourceControlPort,
        base_branch: str,
    ):
        """Worker 子进程入口"""
        logger.info(f"Worker 开始执行: Issue#{task.issue_number}")
        result = agent.execute(task, workspace_path)
        
        # 写结果文件
        result_file = workspace_path.parent / f"result-{task.issue_number}"
        with open(result_file, "w") as f:
            f.write(f"success={result.success}\n")
            f.write(f"message={result.message}\n")
            f.write(f"files={','.join(result.files_changed)}\n")
        
        logger.info(f"Worker 执行完成: Issue#{task.issue_number}, success={result.success}")
    
    def is_worker_alive(self, issue_number: int) -> bool:
        """检查 Worker 进程是否存活"""
        process = self._worker_processes.get(issue_number)
        return process is not None and process.is_alive()
    
    def check_worker_result(self, task: Task) -> ExecutionResult | None:
        """检查 Worker 执行结果"""
        process = self._worker_processes.get(task.issue_number)
        
        # Worker 仍在运行
        if process and process.is_alive():
            return None
        
        # Worker 已结束，检查结果
        workspace = self._workspace_repo.get(task.issue_number)
        if not workspace:
            logger.error(f"工作空间丢失: Issue#{task.issue_number}")
            return ExecutionResult(False, "工作空间丢失")
        
        result_file = workspace.path.parent / f"result-{task.issue_number}"
        
        if not result_file.exists():
            logger.error(f"Worker 异常退出: Issue#{task.issue_number}")
            return ExecutionResult(False, "Worker 异常退出")
        
        try:
            data = {}
            with open(result_file) as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        data[k] = v
            
            result = ExecutionResult(
                success=data.get("success") == "True",
                message=data.get("message", "执行完成"),
                files_changed=data.get("files", "").split(",") if data.get("files") else [],
            )
            
            logger.debug(f"Worker 结果: Issue#{task.issue_number}, success={result.success}")
            return result
        except Exception as e:
            logger.exception(f"读取 Worker 结果失败: {e}")
            return ExecutionResult(False, str(e))
    
    def create_pull_request(self, task: Task) -> PullRequest:
        """创建 Pull Request"""
        logger.info(f"创建 PR: Issue#{task.issue_number}, branch={task.branch_name}")
        
        pr_info = self._source_control.create_pull_request(
            branch_name=task.branch_name,
            title=f"Issue#{task.issue_number}: {task.title}",
            body=f"## 关联 Issue\nCloses #{task.issue_number}\n\n{task.description}",
            base_branch=self._base_branch,
        )
        
        logger.info(f"PR 创建成功: #{pr_info.number} - {pr_info.html_url}")
        
        return PullRequest(
            number=pr_info.number,
            html_url=pr_info.html_url,
            branch_name=pr_info.branch_name,
            title=pr_info.title,
            body=pr_info.body,
        )
    
    def terminate_worker(self, issue_number: int) -> None:
        """终止 Worker"""
        process = self._worker_processes.get(issue_number)
        if process and process.is_alive():
            logger.info(f"终止 Worker: Issue#{issue_number}, PID={process.pid}")
            process.terminate()
            process.join(5)
            if process.is_alive():
                logger.warning(f"强制终止 Worker: Issue#{issue_number}")
                process.kill()
            del self._worker_processes[issue_number]
    
    def terminate_all_workers(self) -> None:
        """终止所有 Worker"""
        logger.info("终止所有 Worker 进程")
        for issue_number in list(self._worker_processes.keys()):
            self.terminate_worker(issue_number)
    
    def cleanup_workspace(self, issue_number: int) -> bool:
        """清理工作空间"""
        logger.info(f"清理工作空间: Issue#{issue_number}")
        return self._workspace_repo.release(issue_number)
    
    def cleanup_stale_workspaces(self, max_age_hours: int = 24) -> int:
        """清理过期工作空间"""
        count = 0
        for ws in self._workspace_repo.list_active():
            age = datetime.now() - ws.created_at
            if age > timedelta(hours=max_age_hours):
                logger.info(f"清理过期工作空间: Issue#{ws.issue_number}, age={age}")
                self._workspace_repo.release(ws.issue_number)
                count += 1
        return count