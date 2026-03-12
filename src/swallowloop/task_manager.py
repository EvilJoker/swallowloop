"""任务持久化管理"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import Config
from .models import Task, TaskState, TaskType


class TaskManager:
    """
    任务管理器 - 负责任务持久化
    
    任务数据保存到 ~/.swallowloop/tasks.json
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.data_dir = config.work_dir or Path.home() / ".swallowloop"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_file = self.data_dir / "tasks.json"
        
        # 加载已有任务
        self._tasks: dict[int, dict] = self._load()
    
    def _load(self) -> dict:
        """加载任务数据"""
        if not self.tasks_file.exists():
            return {}
        
        try:
            with open(self.tasks_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    
    def _save(self) -> None:
        """保存任务数据"""
        with open(self.tasks_file, "w") as f:
            json.dump(self._tasks, f, indent=2, ensure_ascii=False, default=str)
    
    def get(self, issue_number: int) -> Optional[Task]:
        """获取任务"""
        data = self._tasks.get(str(issue_number))
        if not data:
            return None
        
        task = Task(
            task_id=data["task_id"],
            issue_number=data["issue_number"],
            title=data["title"],
            description=data.get("description", ""),
            task_type=TaskType(data.get("task_type", "new_task")),
            branch_name=data.get("branch_name"),
            repo_url=data.get("repo_url"),
        )
        
        # 恢复状态和属性
        task.state = data.get("state", TaskState.NEW.value)
        task.workspace_id = data.get("workspace_id")
        task.pr_number = data.get("pr_number")
        task.pr_url = data.get("pr_url")
        task.retry_count = data.get("retry_count", 0)
        task.submission_count = data.get("submission_count", 0)
        task.comments = data.get("comments", [])
        task.latest_comment = data.get("latest_comment")
        
        return task
    
    def save(self, task: Task) -> None:
        """保存任务"""
        self._tasks[str(task.issue_number)] = {
            "task_id": task.id,
            "issue_number": task.issue_number,
            "title": task.title,
            "description": task.description,
            "task_type": task.task_type.value,
            "state": task.state,
            "branch_name": task.branch_name,
            "repo_url": task.repo_url,
            "workspace_id": task.workspace_id,
            "pr_number": task.pr_number,
            "pr_url": task.pr_url,
            "retry_count": task.retry_count,
            "submission_count": getattr(task, "submission_count", 0),
            "comments": getattr(task, "comments", []),
            "latest_comment": getattr(task, "latest_comment", None),
            "updated_at": datetime.now().isoformat(),
        }
        self._save()
    
    def delete(self, issue_number: int) -> None:
        """删除任务"""
        if str(issue_number) in self._tasks:
            del self._tasks[str(issue_number)]
            self._save()
    
    def list_all(self) -> list[Task]:
        """列出所有任务"""
        tasks = []
        for issue_number in self._tasks:
            task = self.get(int(issue_number))
            if task:
                tasks.append(task)
        return tasks
