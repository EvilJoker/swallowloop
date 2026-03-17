"""JSON 任务仓库实现"""

import json
from datetime import datetime
from pathlib import Path

from ...domain.model import Task, TaskId, TaskState, TaskType, Workspace, Comment, PullRequest
from ...domain.repository import TaskRepository


class JsonTaskRepository(TaskRepository):
    """
    JSON 文件任务仓库
    
    任务数据保存到 ~/.swallowloop/tasks.json
    """
    
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or Path.home() / ".swallowloop"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_file = self.data_dir / "tasks.json"
        
        # 加载已有任务
        self._tasks: dict[str, dict] = self._load()
    
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
    
    def get(self, task_id: TaskId) -> Task | None:
        """根据ID获取任务"""
        # 遍历查找
        for data in self._tasks.values():
            if data.get("task_id") == str(task_id):
                return self._deserialize(data)
        return None
    
    def get_by_issue(self, issue_number: int) -> Task | None:
        """根据Issue编号获取任务"""
        data = self._tasks.get(str(issue_number))
        if not data:
            return None
        return self._deserialize(data)
    
    def save(self, task: Task) -> None:
        """保存任务"""
        self._tasks[str(task.issue_number)] = self._serialize(task)
        self._save()
    
    def list_all(self) -> list[Task]:
        """列出所有任务"""
        return [self._deserialize(data) for data in self._tasks.values()]
    
    def list_active(self) -> list[Task]:
        """列出活跃任务"""
        return [
            task for task in self.list_all()
            if task.is_active
        ]
    
    def list_completed(self) -> list[Task]:
        """列出已完成/已终止的任务"""
        return [
            task for task in self.list_all()
            if not task.is_active
        ]
    
    def delete(self, task_id: TaskId) -> bool:
        """删除任务"""
        for issue_number, data in list(self._tasks.items()):
            if data.get("task_id") == str(task_id):
                del self._tasks[issue_number]
                self._save()
                return True
        return False
    
    def _serialize(self, task: Task) -> dict:
        """序列化任务"""
        return {
            "task_id": str(task.id),
            "issue_number": task.issue_number,
            "title": task.title,
            "description": task.description,
            "task_type": task.task_type.value,
            "state": task.state,
            "branch_name": task.branch_name,
            "repo_url": task.repo_url,
            "workspace_id": task.workspace.id if task.workspace else None,
            "pr_number": task.pr.number if task.pr else None,
            "pr_url": task.pr.html_url if task.pr else None,
            "retry_count": task.retry_count,
            "submission_count": task.submission_count,
            "comments": [
                {
                    "id": c.id,
                    "body": c.body,
                    "author": c.author,
                    "created_at": c.created_at.isoformat(),
                }
                for c in task.comments
            ],
            "updated_at": datetime.now().isoformat(),
        }
    
    def _deserialize(self, data: dict) -> Task:
        """反序列化任务"""
        # 先设置状态，再创建 Task（状态机会读取这个值）
        saved_state = data.get("state", TaskState.NEW.value)
        
        task = Task(
            task_id=TaskId(data["task_id"]),
            issue_number=data["issue_number"],
            title=data["title"],
            description=data.get("description", ""),
            task_type=TaskType(data.get("task_type", "new_task")),
            branch_name=data.get("branch_name"),
            repo_url=data.get("repo_url"),
            initial_state=saved_state,
        )
        
        # 恢复工作空间
        if data.get("workspace_id"):
            task._workspace = Workspace(
                id=data["workspace_id"],
                issue_number=data["issue_number"],
                branch_name=data.get("branch_name", ""),
                path=Path.home() / ".swallowloop" / "workspaces" / data["workspace_id"],
            )
        
        # 恢复 PR
        if data.get("pr_number"):
            task._pr = PullRequest(
                number=data["pr_number"],
                html_url=data.get("pr_url", ""),
                branch_name=data.get("branch_name", ""),
                title=data["title"],
            )
        
        # 恢复计数
        task._retry_count = data.get("retry_count", 0)
        task._submission_count = data.get("submission_count", 0)
        
        # 恢复评论
        for c in data.get("comments", []):
            task._comments.append(Comment(
                id=c["id"],
                body=c["body"],
                author=c.get("author", "unknown"),
                created_at=datetime.fromisoformat(c["created_at"]) if c.get("created_at") else datetime.now(),
            ))
        
        return task
