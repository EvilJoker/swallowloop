"""Orchestrator - 调度层"""

import multiprocessing
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

# 确保 datetime 在全局可用
_ = datetime.now()

from .config import Config
from .github_client import GitHubClient
from .models import Task, TaskState, TaskType, Workspace
from .task_manager import TaskManager
from .worker import TaskResult, Worker
from .workspace_manager import WorkspaceManager


class Orchestrator:
    """
    Orchestrator - 调度层

    职责：
    - Issue 监听
    - 任务生成
    - 代码空间分配
    - 监控任务状态（每10分钟）
    - 指派任务给 Worker

    使用状态机管理任务状态流转
    """

    MONITOR_INTERVAL = 100  # 监控间隔：10分钟

    def __init__(self, config: Config):
        self.config = config
        self.github = GitHubClient(config)
        self.workspace_manager = WorkspaceManager(config)
        self.worker = Worker(config)
        self.task_manager = TaskManager(config)

        # 任务管理
        self.tasks: dict[int, Task] = {}
        self._processed_comments: set[int] = set()

        # 加载已有任务
        self._load_tasks()

        # Worker 进程
        self._worker_processes: dict[int, multiprocessing.Process] = {}
        self._last_monitor_time: datetime | None = None

    def _format_comment(self, task: Task, message: str) -> str:
        """格式化评论
        
        格式: [SwallowLoop Bot][年月日时分秒][提交次数 n] message
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        count = getattr(task, "submission_count", 0) + 1
        return f"[SwallowLoop Bot][{timestamp}][提交次数 {count}] {message}"

    def _load_tasks(self) -> None:
        """加载已有任务"""
        for task in self.task_manager.list_all():
            if task.is_active:
                # 启动时，in_progress 状态的任务应该重置为 pending
                # 因为上次程序可能异常退出，任务未完成
                if task.state == TaskState.IN_PROGRESS.value:
                    task.state = TaskState.PENDING.value
                    print(f"[RESET] Issue#{task.issue_number}: in_progress -> pending (上次未完成)")
                    self._save_task(task)
                self.tasks[task.issue_number] = task

    def _save_task(self, task: Task) -> None:
        """保存任务"""
        self.task_manager.save(task)

    def run(self) -> None:
        """主循环"""
        self._print_banner()

        # 检查 Worker
        available, msg = Worker.check_available()
        if not available:
            print(f"[WARN] Worker 不可用: {msg}")
            return
        print(f"[OK] Worker 就绪: {msg}\n")

        while True:
            try:
                self._scan_issues()
                self._process_tasks()
                self._monitor_tasks()
                self._cleanup()
            except KeyboardInterrupt:
                print("\n\n👋 SwallowLoop 停止")
                self._terminate_all_workers()
                break
            except Exception as e:
                print(f"\n[ERROR] 错误: {e}")

            time.sleep(self.config.poll_interval)

    def _print_banner(self) -> None:
        """打印启动信息"""
        print()
        print("🐦 " + "="*46)
        print("   SwallowLoop · 燕子回环")
        print("="*50)
        print(f"   仓库: {self.config.github_repo}")
        print(f"   标签: {self.config.issue_label}")
        print("="*50)

    # ==================== Issue 扫描 ====================

    def _scan_issues(self) -> None:
        """扫描 Issue"""
        issues = self.github.get_labeled_issues()

        for issue in issues:
            issue_number = issue.number

            # Issue 已关闭
            if issue.state == "closed":
                self._handle_closed_issue(issue_number)
                continue

            # 新 Issue 或已有任务
            if issue_number not in self.tasks:
                self._create_task(issue)
            else:
                self._check_comments(issue)

    def _create_task(self, issue) -> None:
        """创建新任务"""
        branch_name = self._generate_branch_name(issue.number, issue.title)

        task = Task(
            task_id=f"task-{issue.number}",
            issue_number=issue.number,
            title=issue.title,
            description=issue.body or "",
            branch_name=branch_name,
        )

        self.tasks[issue.number] = task
        self._save_task(task)
        print(f"[NEW] Issue#{issue.number}: {issue.title}")
        self._save_task(task)

    def _check_comments(self, issue) -> None:
        """检查评论，触发修改"""
        task = self.tasks.get(issue.number)
        if not task or task.state != TaskState.SUBMITTED.value:
            return

        for comment in issue.get_comments():
            if comment.id in self._processed_comments:
                continue

            # 跳过自己的评论
            if "SwallowLoop" in (comment.body or ""):
                self._processed_comments.add(comment.id)
                continue

            # 用户反馈 → 触发 revise
            task.reset_for_revision(comment.id, comment.body)
            if task.revise():  # 状态机：submitted → pending
                self._processed_comments.add(comment.id)
                print(f"[REVISE] Issue#{issue.number} → 待执行")

    def _handle_closed_issue(self, issue_number: int) -> None:
        """处理关闭的 Issue"""
        task = self.tasks.get(issue_number)
        if not task:
            return

        # 状态机：submitted → completed
        if task.state == TaskState.SUBMITTED.value:
            task.complete()
            print(f"[COMPLETE] Issue#{issue_number}")

        # 清理
        self.workspace_manager.release(issue_number)
        self._terminate_worker(issue_number)

    # ==================== 任务处理 ====================

    def _process_tasks(self) -> None:
        """处理待执行的任务"""
        for task in list(self.tasks.values()):
            # NEW → ASSIGNED
            if task.state == TaskState.NEW.value:
                self._assign_workspace(task)

            # PENDING → IN_PROGRESS
            if task.state == TaskState.PENDING.value:
                self._start_worker(task)

    def _assign_workspace(self, task: Task) -> None:
        """分配工作空间"""
        workspace = self.workspace_manager.allocate(
            task.issue_number,
            task.branch_name
        )
        task.workspace_id = workspace.id

        # 状态机：new → assigned
        task.assign()
        print(f"[ASSIGN] Issue#{task.issue_number} → {workspace.id}")
        print(f"         空间路径: {workspace.path}")

        # 状态机：assigned → pending（准备就绪）
        task.prepare()

    def _start_worker(self, task: Task) -> None:
        """启动 Worker"""
        workspace = self.workspace_manager.get(task.issue_number)
        if not workspace:
            print(f"[ERROR] 找不到代码空间: {task.issue_number}")
            return

        # 启动子进程
        process = multiprocessing.Process(
            target=self._worker_main,
            args=(task, workspace.path, self.config)
        )
        process.start()

        self._worker_processes[task.issue_number] = process
        task.worker_pid = process.pid
        task.started_at = datetime.now()

        # 状态机：pending → in_progress
        task.start()
        print(f"[START] Issue#{task.issue_number} (PID: {process.pid})")
        print(f"        工作目录: {workspace.path}")

        # 通知
        msg = "开始处理此 Issue" if task.task_type == TaskType.NEW_TASK else "根据反馈修改代码中..."
        comment = self._format_comment(task, f"{msg}\n\n分支: `{task.branch_name}`")
        self.github.comment_on_issue(task.issue_number, comment)
        print(f"[COMMENT] Issue#{task.issue_number}: {msg}")
        self._save_task(task)

    @staticmethod
    def _worker_main(task: Task, workspace_path: Path, config: Config):
        """Worker 子进程入口"""
        worker = Worker(config)
        result = worker.execute(task, workspace_path)

        # 写结果文件
        result_file = workspace_path.parent / f"result-{task.issue_number}"
        with open(result_file, "w") as f:
            f.write(f"success={result.success}\n")
            f.write(f"message={result.message}\n")
            f.write(f"files={','.join(result.files_changed)}\n")

    # ==================== 状态监控 ====================

    def _monitor_tasks(self) -> None:
        """监控任务状态（每10分钟）"""
        now = datetime.now()

        if self._last_monitor_time:
            if (now - self._last_monitor_time).total_seconds() < self.MONITOR_INTERVAL:
                return

        self._last_monitor_time = now

        for task in list(self.tasks.values()):
            if task.state != TaskState.IN_PROGRESS.value:
                continue

            process = self._worker_processes.get(task.issue_number)

            # Worker 已结束，检查结果
            if not process or not process.is_alive():
                self._check_result(task)

    def _check_result(self, task: Task) -> None:
        """检查执行结果"""
        workspace = self.workspace_manager.get(task.issue_number)
        if not workspace:
            self._handle_failure(task, "代码空间丢失")
            return

        result_file = workspace.path.parent / f"result-{task.issue_number}"

        if not result_file.exists():
            self._handle_failure(task, "Worker 异常退出")
            return

        try:
            data = {}
            with open(result_file) as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        data[k] = v

            if data.get("success") == "True":
                self._handle_success(task)
            else:
                self._handle_failure(task, data.get("message", "执行失败"))

        except Exception as e:
            self._handle_failure(task, str(e))

    def _handle_success(self, task: Task) -> None:
        """处理成功"""
        workspace = self.workspace_manager.get(task.issue_number)
        if not workspace:
            return

        # 创建或获取 PR
        pr = self.github.create_pr(
            issue_number=task.issue_number,
            branch_name=task.branch_name,
            title=task.title,
            body=f"## 关联 Issue\nCloses #{task.issue_number}\n\n{task.description}",
            existing_pr_number=task.pr_number,
        )

        task.pr_number = pr.number
        task.pr_url = pr.html_url
        task.submission_count = getattr(task, "submission_count", 0) + 1

        # 状态机：in_progress → submitted
        task.submit()
        print(f"[SUBMIT] Issue#{task.issue_number} → PR #{pr.number}")
        
        comment = self._format_comment(task, f"代码已提交\n\nPR: {pr.html_url}\n\n请审查后合并。")
        self.github.comment_on_issue(task.issue_number, comment)
        print(f"[COMMENT] Issue#{task.issue_number}: 代码已提交 PR #{pr.number}")
        self._save_task(task)
    
    def _handle_failure(self, task: Task, reason: str) -> None:
        """处理失败"""
        task.increment_retry()

        if task.is_retryable:
            # 状态机：in_progress → pending（重试）
            if task.retry():
                print(f"[RETRY {task.retry_count}/{task.max_retries}] Issue#{task.issue_number}: {reason}")
            else:
                # 重试条件不满足，终止
                task.abort()
                print(f"[ABORT] Issue#{task.issue_number}: {reason}")
                self._notify_abort(task, reason)
        else:
            # 已达最大重试，终止
            task.abort()
            print(f"[ABORT] Issue#{task.issue_number}: 重试次数耗尽")
            self._notify_abort(task, f"已重试 {task.max_retries} 次: {reason}")

    def _notify_abort(self, task: Task, reason: str) -> None:
        """通知异常终止"""
        comment = self._format_comment(task, f"任务异常终止\n\n原因: {reason}\n\n请人工处理。")
        self.github.comment_on_issue(task.issue_number, comment)
        print(f"[COMMENT] Issue#{task.issue_number}: 任务异常终止 - {reason}")
        self._save_task(task)

    # ==================== 清理 ====================

    def _cleanup(self) -> None:
        """清理资源"""
        # 清理过期代码空间
        cleaned = self.workspace_manager.cleanup_stale(24)
        if cleaned:
            print(f"[CLEANUP] 清理 {cleaned} 个过期代码空间")

        # 清理已完成/终止的任务
        for issue_number, task in list(self.tasks.items()):
            if not task.is_active:
                if (datetime.now() - task.updated_at) > timedelta(hours=1):
                    del self.tasks[issue_number]

    def _terminate_worker(self, issue_number: int) -> None:
        """终止 Worker"""
        process = self._worker_processes.get(issue_number)
        if process and process.is_alive():
            process.terminate()
            process.join(5)
            if process.is_alive():
                process.kill()
            del self._worker_processes[issue_number]

    def _terminate_all_workers(self) -> None:
        """终止所有 Worker"""
        for issue_number in list(self._worker_processes.keys()):
            self._terminate_worker(issue_number)

    # ==================== 工具 ====================

    def _generate_branch_name(self, issue_number: int, title: str) -> str:
        """生成分支名"""
        slug = re.sub(r"[^a-zA-Z0-9\s-]", "", title.lower())
        slug = re.sub(r"[\s]+", "-", slug).strip("-")[:30]
        return f"Issue{issue_number}_{slug}"
