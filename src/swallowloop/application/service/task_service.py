"""任务应用服务"""

import re
from datetime import datetime
from pathlib import Path
from typing import Protocol

from ...domain.model import Task, TaskId, TaskState, TaskType, Workspace, Comment
from ...domain.repository import TaskRepository, WorkspaceRepository
from ..dto import IssueDTO, TaskDTO, WorkspaceDTO


class SourceControlPort(Protocol):
    """源码控制端口"""
    def get_labeled_issues(self, label: str) -> list[IssueDTO]: ...
    def get_issue_comments(self, issue_number: int) -> list[Comment]: ...
    def comment_on_issue(self, issue_number: int, body: str) -> None: ...
    def get_clone_url(self) -> str: ...
    def get_pull_request(self, pr_number: int): ...


class TaskService:
    """
    任务应用服务
    
    负责任务的生命周期管理
    """
    
    def __init__(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        source_control: SourceControlPort,
        issue_label: str = "swallow",
        base_branch: str = "main",
    ):
        self._task_repo = task_repository
        self._workspace_repo = workspace_repository
        self._source_control = source_control
        self._issue_label = issue_label
        self._base_branch = base_branch
        self._processed_comments: set[int] = set()
    
    def scan_issues(self) -> tuple[list[Task], list[Task]]:
        """
        扫描 Issue 并创建/更新任务
        
        Returns:
            tuple: (新任务列表, 需要中止的任务列表)
        """
        # 1. 获取远端打开的 Issue 列表
        open_issues = self._source_control.get_labeled_issues(self._issue_label)
        open_issue_numbers = {issue.number for issue in open_issues}
        
        # 2. 获取本地活跃任务
        local_tasks = self._task_repo.list_active()
        
        tasks = []
        tasks_to_abort = []
        
        # 3. 检查本地任务：如果 Issue 已关闭（不在打开列表中），则需要处理
        for task in local_tasks:
            if task.issue_number not in open_issue_numbers:
                # Issue 已关闭
                if task.state == TaskState.SUBMITTED.value:
                    # 检查 PR 是否合并
                    if task.pr and self._is_pr_merged(task.pr.number):
                        # PR 已合并，任务完成
                        task.complete()
                        self._task_repo.save(task)
                    else:
                        # PR 未合并，中止任务
                        tasks_to_abort.append(task)
                elif task.state in (TaskState.IN_PROGRESS.value, TaskState.PENDING.value, 
                                    TaskState.NEW.value, TaskState.ASSIGNED.value):
                    # 任务执行中或待执行，需要中止
                    tasks_to_abort.append(task)
        
        # 4. 检查远端 Issue：创建新任务或检查评论
        for issue in open_issues:
            task = self._task_repo.get_by_issue(issue.number)
            
            if task is None:
                # 本地无此任务，创建新任务
                task = self._create_task_from_issue(issue)
                tasks.append(task)
            else:
                # 本地已有任务，检查评论
                self._check_comments(task, issue.number)
        
        return tasks, tasks_to_abort
    
    def _is_pr_merged(self, pr_number: int) -> bool:
        """检查 PR 是否已合并"""
        try:
            pr = self._source_control.get_pull_request(pr_number)
            return pr.merged
        except Exception:
            return False
    
    def _create_task_from_issue(self, issue: IssueDTO) -> Task:
        """从 Issue 创建任务"""
        branch_name = self._generate_branch_name(issue.number, issue.title)
        
        task = Task(
            task_id=TaskId(f"task-{issue.number}"),
            issue_number=issue.number,
            title=issue.title,
            description=issue.body or "",
            branch_name=branch_name,
        )
        
        self._task_repo.save(task)
        return task
    
    def _check_comments(self, task: Task, issue_number: int) -> None:
        """检查评论，触发修改"""
        if task.state != TaskState.SUBMITTED.value:
            return
        
        comments = self._source_control.get_issue_comments(issue_number)
        
        for comment in comments:
            if comment.id in self._processed_comments:
                continue
            
            # 跳过自己的评论
            if comment.is_bot_comment:
                self._processed_comments.add(comment.id)
                continue
            
            # 用户反馈 → 触发 revise
            task.apply_revision(comment)
            self._task_repo.save(task)
            self._processed_comments.add(comment.id)
    
    def assign_workspace(self, task: Task) -> Workspace:
        """为任务分配工作空间"""
        from datetime import datetime
        
        # 创建工作空间
        workspace_id = f"issue{task.issue_number}_{datetime.now().strftime('%Y%m%d')}"
        workspace_path = self._get_workspace_path(workspace_id)
        
        workspace = Workspace(
            id=workspace_id,
            issue_number=task.issue_number,
            branch_name=task.branch_name,
            path=workspace_path,
        )
        
        # 设置仓库 URL
        task._repo_url = self._source_control.get_clone_url()
        
        # 分配工作空间
        task.assign_workspace(workspace)
        task.mark_ready()
        
        # 保存
        self._workspace_repo.save(workspace)
        self._task_repo.save(task)
        
        return workspace
    
    def start_task(self, task: Task) -> None:
        """开始任务"""
        task.begin_execution()
        self._task_repo.save(task)
    
    def submit_task(self, task: Task, pr_number: int, pr_url: str) -> None:
        """提交任务"""
        from ...domain.model import PullRequest
        
        pr = PullRequest(
            number=pr_number,
            html_url=pr_url,
            branch_name=task.branch_name,
            title=task.title,
        )
        task.submit_pr(pr)
        self._task_repo.save(task)
    
    def complete_task(self, task: Task) -> None:
        """完成任务"""
        task.mark_completed()
        self._task_repo.save(task)
    
    def abort_task(self, task: Task, reason: str) -> None:
        """终止任务"""
        task.do_abort()
        self._task_repo.save(task)
    
    def retry_task(self, task: Task, reason: str) -> None:
        """重试任务"""
        task.increment_retry()
        task.do_retry()
        self._task_repo.save(task)
    
    def get_pending_tasks(self) -> list[Task]:
        """获取待执行任务"""
        return [
            task for task in self._task_repo.list_active()
            if task.state in (TaskState.NEW.value, TaskState.PENDING.value)
        ]
    
    def get_in_progress_tasks(self) -> list[Task]:
        """获取执行中任务"""
        return [
            task for task in self._task_repo.list_active()
            if task.state == TaskState.IN_PROGRESS.value
        ]
    
    def comment_on_issue(self, issue_number: int, message: str) -> None:
        """在 Issue 上评论"""
        self._source_control.comment_on_issue(issue_number, message)
    
    def format_comment(self, task: Task, message: str) -> str:
        """格式化评论"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        count = task.submission_count + 1
        return f"[SwallowLoop Bot][{timestamp}][提交次数 {count}] {message}"
    
    def _generate_branch_name(self, issue_number: int, title: str) -> str:
        """生成分支名"""
        slug = re.sub(r"[^a-zA-Z0-9\s-]", "", title.lower())
        slug = re.sub(r"[\s]+", "-", slug).strip("-")[:30]
        return f"Issue{issue_number}_{slug}"
    
    def _get_workspace_path(self, workspace_id: str) -> Path:
        """获取工作空间路径"""
        workspaces_dir = Path.home() / ".swallowloop" / "workspaces"
        workspaces_dir.mkdir(parents=True, exist_ok=True)
        return workspaces_dir / workspace_id
