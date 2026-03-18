"""执行应用服务"""

import logging
import multiprocessing
import os
import traceback
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
    WORKER_TIMEOUT_HOURS = 2  # Worker 超时时间：2小时
    
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
        self._worker_start_times: dict[int, datetime] = {}  # 记录启动时间
        self._last_monitor_time: datetime | None = None
    
    def start_worker(self, task: Task) -> None:
        """启动 Worker 进程"""
        workspace = self._workspace_repo.get(task.issue_number)
        if not workspace:
            raise ValueError(f"工作空间不存在: Issue#{task.issue_number}")
        
        # 清理可能存在的旧结果文件
        result_file = workspace.path.parent / f"result-{task.issue_number}"
        if result_file.exists():
            result_file.unlink()
            logger.debug(f"清理旧结果文件: {result_file}")
        
        # 启动子进程
        process = multiprocessing.Process(
            target=self._worker_main,
            args=(task, workspace.path, self._agent, self._source_control, self._base_branch),
        )
        process.start()
        
        self._worker_processes[task.issue_number] = process
        self._worker_start_times[task.issue_number] = datetime.now()  # 记录启动时间
        task._worker_pid = process.pid
        task._started_at = datetime.now()
        
        logger.info(f"Worker 进程已启动: Issue#{task.issue_number}, PID={process.pid}")
        logger.info(f"当前活跃 Worker 数量: {len(self._worker_processes)}")
    
    @staticmethod
    def _worker_main(
        task: Task,
        workspace_path: Path,
        agent: AgentPort,
        source_control: SourceControlPort,
        base_branch: str,
    ):
        """Worker 子进程入口"""
        result_file = workspace_path.parent / f"result-{task.issue_number}"
        
        try:
            logger.info(f"Worker 开始执行: Issue#{task.issue_number}, PID={os.getpid()}")
            result = agent.execute(task, workspace_path)
            
            # 写结果文件
            with open(result_file, "w") as f:
                f.write(f"success={result.success}\n")
                f.write(f"message={result.message}\n")
                f.write(f"files={','.join(result.files_changed)}\n")
                f.write(f"commit_message={result.commit_message}\n")
            
            logger.info(f"Worker 执行完成: Issue#{task.issue_number}, success={result.success}")
            
        except Exception as e:
            # 捕获所有异常，确保生成结果文件
            error_msg = f"Worker 异常退出: {str(e)}\n{traceback.format_exc()}"
            logger.error(f"Issue#{task.issue_number} {error_msg}")
            
            # 写入错误结果
            try:
                with open(result_file, "w") as f:
                    f.write(f"success=False\n")
                    f.write(f"message={error_msg}\n")
                    f.write(f"files=\n")
                    f.write(f"commit_message=\n")
            except Exception as write_error:
                logger.error(f"写入结果文件失败: {write_error}")
    
    def check_worker_result(self, task: Task) -> ExecutionResult | None:
        """检查 Worker 执行结果
        
        Returns:
            None: Worker 仍在执行或超时等待确认
            ExecutionResult: Worker 已完成或异常
        """
        process = self._worker_processes.get(task.issue_number)
        start_time = self._worker_start_times.get(task.issue_number)
        
        # 检查超时（即使进程不在字典中，也要检查任务开始时间）
        if start_time:
            elapsed = datetime.now() - start_time
            if elapsed > timedelta(hours=self.WORKER_TIMEOUT_HOURS):
                logger.warning(f"Worker 超时: Issue#{task.issue_number}, 已运行 {elapsed}")
                # 终止进程
                if process and process.is_alive():
                    logger.info(f"终止超时 Worker: Issue#{task.issue_number}")
                    process.terminate()
                    process.join(5)
                    if process.is_alive():
                        process.kill()
                return ExecutionResult(False, f"Worker 超时 (运行超过 {self.WORKER_TIMEOUT_HOURS} 小时)")
        
        # Worker 仍在运行
        if process and process.is_alive():
            return None
        
        # 进程不在字典中，但任务状态是 IN_PROGRESS（可能是主进程重启）
        if not process:
            logger.warning(f"Worker 进程信息丢失: Issue#{task.issue_number}，检查结果文件")
        
        # Worker 已结束或进程信息丢失，检查结果
        workspace = self._workspace_repo.get(task.issue_number)
        if not workspace:
            logger.error(f"工作空间丢失: Issue#{task.issue_number}")
            return ExecutionResult(False, "工作空间丢失")
        
        result_file = workspace.path.parent / f"result-{task.issue_number}"
        
        if not result_file.exists():
            logger.error(f"Worker 异常退出: Issue#{task.issue_number}，无结果文件")
            return ExecutionResult(False, "Worker 异常退出，无结果文件")
        
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
                commit_message=data.get("commit_message", ""),
            )
            
            logger.info(f"Worker 结果: Issue#{task.issue_number}, success={result.success}")
            if result.commit_message:
                logger.info(f"Commit message: {result.commit_message}")
            
            # 清理进程记录
            if task.issue_number in self._worker_processes:
                del self._worker_processes[task.issue_number]
            if task.issue_number in self._worker_start_times:
                del self._worker_start_times[task.issue_number]
            
            return result
        except Exception as e:
            logger.exception(f"读取 Worker 结果失败: {e}")
            return ExecutionResult(False, str(e))
    
    def create_pull_request(self, task: Task, commit_message: str = "") -> PullRequest:
        """创建 Pull Request
        
        Args:
            task: 任务对象
            commit_message: AI 生成的 commit message，用于 PR 标题
        """
        logger.info(f"创建 PR: Issue#{task.issue_number}, branch={task.branch_name}")
        
        # 使用 AI 生成的 commit message 作为 PR 标题，否则生成一个
        pr_title = commit_message if commit_message else self._generate_pr_title(task)
        
        pr_info = self._source_control.create_pull_request(
            branch_name=task.branch_name,
            title=pr_title,
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
    
    def _generate_pr_title(self, task: Task) -> str:
        """生成简洁的 PR 标题
        
        格式: {type}: {简短描述}
        
        例如：
        - "feat: 自更新机制"
        - "fix: 修复工作空间 origin 指向问题"
        """
        # 获取类型前缀
        pr_type = self._get_pr_type(task.labels or [])
        
        # 从标题提取简短描述
        summary = self._extract_summary(task.title)
        
        return f"{pr_type}: {summary}"
    
    def _get_pr_type(self, labels: list[str]) -> str:
        """根据标签获取 PR 类型"""
        label_set = {label.lower() for label in labels}
        
        if label_set & {"bug", "fix", "defect"}:
            return "fix"
        if label_set & {"documentation", "docs", "document"}:
            return "docs"
        if label_set & {"chore", "refactor", "maintenance"}:
            return "chore"
        if label_set & {"test", "testing"}:
            return "test"
        
        return "feat"
    
    def _extract_summary(self, title: str) -> str:
        """从 Issue 标题提取简短描述"""
        import re
        
        # 常见冗余词汇
        filler_words = ["每次", "当我", "我想", "然后", "如果", "有就", "可以", "能够", "应该"]
        
        summary = title
        for word in filler_words:
            summary = summary.replace(word, "")
        
        # 提取第一句话
        for sep in ["。", "，", ",", "\n", "；", ";"]:
            if sep in summary:
                summary = summary.split(sep)[0]
                break
        
        # 清理空白
        summary = re.sub(r"\s+", "", summary).strip()
        
        # 限制长度
        if len(summary) > 30:
            summary = summary[:30]
        
        return summary or title[:30]
    
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
    
    def get_active_worker_count(self) -> int:
        """获取活跃 Worker 数量（实际正在运行的进程数）
        
        会先清理已结束的进程记录
        """
        # 清理已结束的进程记录
        dead_issues = []
        for issue_number, process in self._worker_processes.items():
            if not process.is_alive():
                dead_issues.append(issue_number)
        
        for issue_number in dead_issues:
            del self._worker_processes[issue_number]
            if issue_number in self._worker_start_times:
                del self._worker_start_times[issue_number]
            logger.debug(f"清理已结束的 Worker 记录: Issue#{issue_number}")
        
        return len(self._worker_processes)
    
    def get_running_issue_numbers(self) -> list[int]:
        """获取正在运行的 Issue 编号列表"""
        return list(self._worker_processes.keys())
    
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